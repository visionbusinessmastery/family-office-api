import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.gamification.progress_service import award_xp
from intelligence.user_intelligence_engine import compute_user_intelligence
from product.entitlements import (
    MODULE_REGISTRY,
    build_entitlements,
    can_access_module,
    normalize_plan,
    plan_allows,
    resolve_effective_plan,
)
from product.daily_briefing import build_ceo_daily_briefing


router = APIRouter()
_product_schema_ready = False


class DailyBriefingActionRequest(BaseModel):
    action_key: str
    action_label: str | None = None
    action_title: str | None = None
    action_description: str | None = None
    mission_key: str | None = None
    briefing_version: str | None = None


class DailyActionTaskUpdateRequest(BaseModel):
    status: str


def ensure_product_tables(conn):
    global _product_schema_ready

    if _product_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS progression_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            xp INTEGER NOT NULL DEFAULT 0,
            level_name TEXT NOT NULL DEFAULT 'Builder',
            status TEXT NOT NULL DEFAULT 'Foundation',
            streak INTEGER NOT NULL DEFAULT 0,
            last_seen_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS xp_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_module_states (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            module_key TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'locked',
            completed_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS user_module_states_unique
        ON user_module_states(user_id, module_key)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            action_label TEXT,
            action_url TEXT,
            status TEXT NOT NULL DEFAULT 'unread',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS daily_briefing_actions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            action_key TEXT NOT NULL,
            action_label TEXT,
            action_title TEXT,
            action_description TEXT,
            briefing_version TEXT,
            status TEXT NOT NULL DEFAULT 'recorded',
            xp_awarded INTEGER NOT NULL DEFAULT 0,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS daily_briefing_actions_user_created_idx
        ON daily_briefing_actions(user_id, created_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS daily_action_tasks (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'ceo_daily_briefing',
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            mission_key TEXT,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'todo',
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS daily_action_tasks_user_status_idx
        ON daily_action_tasks(user_id, status, created_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS academy_progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            lesson_key TEXT NOT NULL,
            module_key TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            xp_awarded INTEGER NOT NULL DEFAULT 0,
            completed_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS academy_progress_user_lesson_unique
        ON academy_progress(user_id, lesson_key)
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS academy_progress_user_completed_idx
        ON academy_progress(user_id, completed_at DESC)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS mission_progress (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            mission_key TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'completed',
            xp_awarded INTEGER NOT NULL DEFAULT 0,
            completed_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS mission_progress_user_mission_unique
        ON mission_progress(user_id, mission_key)
    """))

    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_founder BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_tier TEXT"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS founder_discount INTEGER DEFAULT 0"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS level TEXT DEFAULT 'BEGINNER'"))

    _product_schema_ready = True


def safe_count(conn, query: str, params: dict):
    try:
        return int(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0


def safe_float(conn, query: str, params: dict):
    try:
        return float(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0.0


def get_score(email: str) -> int:
    try:
        result = compute_user_intelligence(email) or {}
        return int(result.get("global_score") or result.get("score") or 0)
    except Exception:
        return 0


def compute_level(score: int, xp: int):
    if score >= 95 or xp >= 9000:
        return "Dynasty Architect"
    if score >= 88 or xp >= 6500:
        return "Legacy Builder"
    if score >= 85 or xp >= 5000:
        return "Family Office Operator"
    if score >= 75 or xp >= 3000:
        return "Elite Investor"
    if score >= 60 or xp >= 1800:
        return "Investor"
    if score >= 45 or xp >= 900:
        return "Advanced"
    if score >= 25 or xp >= 300:
        return "Builder"
    return "Beginner"


def compute_status(score: int, plan: str):
    if plan_allows(plan, "LEGACY"):
        return "Dynasty Office"
    if plan_allows(plan, "LIBERTY"):
        return "Sovereign Wealth"
    if plan_allows(plan, "ELITE"):
        return "Wealth OS"
    if score >= 70:
        return "Acceleration"
    if score >= 40:
        return "Growth"
    return "Foundation"


def get_next_plan(plan: str):
    normalized = normalize_plan(plan)
    if not plan_allows(normalized, "GOLD"):
        return "gold"
    if not plan_allows(normalized, "ELITE"):
        return "elite"
    if not plan_allows(normalized, "LIBERTY"):
        return "liberty"
    if not plan_allows(normalized, "LEGACY"):
        return "legacy"
    return None


def get_effective_plan_for_user(conn, user_id: int):
    plan_row = conn.execute(text("""
        SELECT
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.id = :user_id
    """), {"user_id": user_id}).fetchone()

    return resolve_effective_plan(
        plan_row.user_plan if plan_row else "FREE",
        plan_row.subscription_plan if plan_row else None,
        plan_row.subscription_status if plan_row else None,
    )


@router.post("/daily-briefing/action")
def record_daily_briefing_action(
    payload: DailyBriefingActionRequest,
    email: str = Depends(get_current_user),
):
    action_key = (payload.action_key or "").strip().lower()
    status = daily_action_status(action_key)

    if not status:
        raise HTTPException(status_code=400, detail="Action briefing inconnue")

    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_product_tables(conn)

        existing = conn.execute(text("""
            SELECT id, status, xp_awarded, created_at
            FROM daily_briefing_actions
            WHERE user_id = :user_id
              AND action_key = :action_key
              AND created_at::date = CURRENT_DATE
            ORDER BY created_at DESC
            LIMIT 1
        """), {
            "user_id": user_id,
            "action_key": action_key,
        }).fetchone()

        if existing:
            loop = get_daily_briefing_loop(conn, user_id)
            return {
                "recorded": False,
                "already_recorded": True,
                "action_key": action_key,
                "status": existing.status,
                "xp_awarded": int(existing.xp_awarded or 0),
                "message": "Action deja enregistree aujourd'hui.",
                "daily_loop": loop,
            }

        xp_amount = daily_action_xp(action_key)
        metadata = {
            "source": "ceo_daily_briefing",
            "briefing_version": payload.briefing_version,
            "action_title": payload.action_title,
            "action_description": payload.action_description,
            "mission_key": payload.mission_key,
        }

        xp_result = award_xp(
            conn,
            user_id,
            email,
            f"daily_briefing_{action_key}",
            xp_amount,
            metadata,
        )
        xp_awarded = int(xp_result.get("awarded") or 0)

        conn.execute(text("""
            INSERT INTO daily_briefing_actions (
                user_id, action_key, action_label, action_title,
                action_description, briefing_version, status, xp_awarded, metadata
            )
            VALUES (
                :user_id, :action_key, :action_label, :action_title,
                :action_description, :briefing_version, :status, :xp_awarded,
                CAST(:metadata AS JSONB)
            )
        """), {
            "user_id": user_id,
            "action_key": action_key,
            "action_label": payload.action_label,
            "action_title": payload.action_title,
            "action_description": payload.action_description,
            "briefing_version": payload.briefing_version,
            "status": status,
            "xp_awarded": xp_awarded,
            "metadata": json.dumps(metadata),
        })

        if action_key == "automate":
            task_title = payload.action_title or "Action patrimoniale a automatiser"
            task_description = (
                payload.action_description
                or "Action creee depuis le briefing quotidien White Rock."
            )
            duplicate_task = conn.execute(text("""
                SELECT id
                FROM daily_action_tasks
                WHERE user_id = :user_id
                  AND source = 'ceo_daily_briefing'
                  AND title = :title
                  AND description = :description
                  AND status IN ('todo', 'in_progress')
                ORDER BY created_at DESC
                LIMIT 1
            """), {
                "user_id": user_id,
                "title": task_title,
                "description": task_description,
            }).fetchone()

            if not duplicate_task:
                conn.execute(text("""
                    INSERT INTO daily_action_tasks (
                        user_id, source, title, description, mission_key,
                        priority, status, metadata
                    )
                    VALUES (
                        :user_id, 'ceo_daily_briefing', :title, :description,
                        :mission_key, :priority, 'todo', CAST(:metadata AS JSONB)
                    )
                """), {
                    "user_id": user_id,
                    "title": task_title,
                    "description": task_description,
                    "mission_key": payload.mission_key,
                    "priority": "high" if payload.mission_key else "normal",
                    "metadata": json.dumps(metadata),
                })

            conn.execute(text("""
                INSERT INTO notifications (user_id, type, title, message, action_label, action_url)
                VALUES (
                    :user_id,
                    'daily_briefing',
                    'Automatisation demandee',
                    :message,
                    'Voir le briefing',
                    '/dashboard'
                )
            """), {
                "user_id": user_id,
                "message": payload.action_description
                or "White Rock a note cette action comme candidate a l'automatisation.",
            })

        loop = get_daily_briefing_loop(conn, user_id)

    return {
        "recorded": True,
        "already_recorded": False,
        "action_key": action_key,
        "status": status,
        "xp_awarded": xp_awarded,
        "xp": xp_result.get("xp"),
        "level": xp_result.get("level"),
        "message": (
            "Decision enregistree."
            if action_key == "decide"
            else "Action ignoree pour aujourd'hui."
            if action_key == "ignore"
            else "Automatisation ajoutee a la file de travail."
        ),
        "daily_loop": loop,
    }


@router.post("/daily-briefing/tasks/{task_id}/status")
def update_daily_action_task_status(
    task_id: int,
    payload: DailyActionTaskUpdateRequest,
    email: str = Depends(get_current_user),
):
    status = (payload.status or "").strip().lower()
    allowed = {"todo", "in_progress", "done", "cancelled"}

    if status not in allowed:
        raise HTTPException(status_code=400, detail="Statut de tache inconnu")

    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_product_tables(conn)

        task = conn.execute(text("""
            SELECT id, status, title, description, mission_key
            FROM daily_action_tasks
            WHERE id = :task_id
              AND user_id = :user_id
        """), {
            "task_id": task_id,
            "user_id": user_id,
        }).fetchone()

        if not task:
            raise HTTPException(status_code=404, detail="Tache introuvable")

        xp_result = {"awarded": 0}
        if status == "done" and task.status != "done":
            xp_result = award_xp(
                conn,
                user_id,
                email,
                "daily_action_task_done",
                30,
                {
                    "task_id": task_id,
                    "title": task.title,
                    "mission_key": task.mission_key,
                    "source": "ceo_daily_briefing",
                },
            )

        conn.execute(text("""
            UPDATE daily_action_tasks
            SET status = :status,
                updated_at = NOW(),
                completed_at = CASE WHEN :status = 'done' THEN NOW() ELSE completed_at END
            WHERE id = :task_id
              AND user_id = :user_id
        """), {
            "status": status,
            "task_id": task_id,
            "user_id": user_id,
        })

        loop = get_daily_briefing_loop(conn, user_id)

    return {
        "updated": True,
        "task_id": task_id,
        "status": status,
        "xp_awarded": int(xp_result.get("awarded") or 0),
        "message": "Tache mise a jour.",
        "daily_loop": loop,
    }


@router.post("/academy/lessons/{lesson_key}/complete")
def complete_academy_lesson(
    lesson_key: str,
    email: str = Depends(get_current_user),
):
    normalized_lesson_key = (lesson_key or "").strip()

    if not normalized_lesson_key:
        raise HTTPException(status_code=400, detail="Lecon Academy inconnue")

    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_product_tables(conn)

        plan = get_effective_plan_for_user(conn, user_id)
        score = get_score(email)
        progress = get_academy_progress(conn, user_id)
        mission_progress = get_mission_progress(conn, user_id)
        data_profile = build_data_profile(conn, user_id)
        missions = build_missions(data_profile, score, plan, progress, mission_progress)
        academy = build_wealth_academy(data_profile, missions, score, plan, progress)
        lessons = {
            lesson.get("key"): {
                **lesson,
                "module_key": module.get("key"),
                "module_title": module.get("title"),
            }
            for module in academy.get("modules", [])
            for lesson in module.get("lessons", [])
        }
        lesson = lessons.get(normalized_lesson_key)

        if not lesson:
            raise HTTPException(status_code=404, detail="Lecon Academy introuvable")

        if lesson.get("completed"):
            return {
                "completed": False,
                "already_completed": True,
                "lesson_key": normalized_lesson_key,
                "xp_awarded": int(lesson.get("xp_awarded") or 0),
                "message": "Lecon deja validee.",
                "wealth_academy": academy,
            }

        xp_result = award_xp(
            conn,
            user_id,
            email,
            "academy_lesson_completed",
            academy_lesson_xp(),
            {
                "source": "wealth_academy",
                "lesson_key": normalized_lesson_key,
                "lesson_title": lesson.get("title"),
                "module_key": lesson.get("module_key"),
                "module_title": lesson.get("module_title"),
            },
        )
        xp_awarded = int(xp_result.get("awarded") or 0)

        conn.execute(text("""
            INSERT INTO academy_progress (
                user_id,
                lesson_key,
                module_key,
                status,
                xp_awarded,
                completed_at,
                updated_at
            )
            VALUES (
                :user_id,
                :lesson_key,
                :module_key,
                'completed',
                :xp_awarded,
                NOW(),
                NOW()
            )
            ON CONFLICT (user_id, lesson_key) DO UPDATE
            SET status = 'completed',
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "lesson_key": normalized_lesson_key,
            "module_key": lesson.get("module_key"),
            "xp_awarded": xp_awarded,
        })

        progress = get_academy_progress(conn, user_id)
        academy = build_wealth_academy(data_profile, missions, score, plan, progress)

    return {
        "completed": True,
        "already_completed": False,
        "lesson_key": normalized_lesson_key,
        "xp_awarded": xp_awarded,
        "message": "Lecon validee. Progression Academy mise a jour.",
        "wealth_academy": academy,
    }


@router.post("/missions/{mission_key}/complete")
def complete_product_mission(
    mission_key: str,
    email: str = Depends(get_current_user),
):
    normalized_mission_key = (mission_key or "").strip()

    if not normalized_mission_key:
        raise HTTPException(status_code=400, detail="Mission inconnue")

    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        ensure_product_tables(conn)

        plan = get_effective_plan_for_user(conn, user_id)
        score = get_score(email)
        data_profile = build_data_profile(conn, user_id)
        academy_progress = get_academy_progress(conn, user_id)
        mission_progress = get_mission_progress(conn, user_id)
        missions = build_missions(data_profile, score, plan, academy_progress, mission_progress)
        mission = next((item for item in missions if item.get("key") == normalized_mission_key), None)

        if not mission:
            raise HTTPException(status_code=404, detail="Mission introuvable")

        if mission.get("completed"):
            return {
                "completed": False,
                "already_completed": True,
                "mission_key": normalized_mission_key,
                "xp_awarded": int(mission.get("xp_awarded") or 0),
                "message": "Mission deja validee.",
                "missions": missions,
            }

        if mission.get("status") != "ready":
            raise HTTPException(status_code=400, detail="Mission pas encore prete")

        xp_amount = int(mission.get("xp") or 0)
        xp_result = award_xp(
            conn,
            user_id,
            email,
            "product_mission_completed",
            xp_amount,
            {
                "source": "product_missions",
                "mission_key": normalized_mission_key,
                "mission_title": mission.get("title"),
                "impact_dimension": mission.get("impact_dimension"),
            },
        )
        xp_awarded = int(xp_result.get("awarded") or 0)

        conn.execute(text("""
            INSERT INTO mission_progress (
                user_id,
                mission_key,
                status,
                xp_awarded,
                completed_at,
                updated_at
            )
            VALUES (
                :user_id,
                :mission_key,
                'completed',
                :xp_awarded,
                NOW(),
                NOW()
            )
            ON CONFLICT (user_id, mission_key) DO NOTHING
        """), {
            "user_id": user_id,
            "mission_key": normalized_mission_key,
            "xp_awarded": xp_awarded,
        })

        mission_progress = get_mission_progress(conn, user_id)
        missions = build_missions(data_profile, score, plan, academy_progress, mission_progress)

    return {
        "completed": True,
        "already_completed": False,
        "mission_key": normalized_mission_key,
        "xp_awarded": xp_awarded,
        "message": "Mission validee. XP et progression mis a jour.",
        "missions": missions,
    }


def build_progression(conn, user_id: int, score: int, plan: str):
    ensure_product_tables(conn)

    row = conn.execute(text("""
        SELECT xp, streak
        FROM progression_profiles
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        conn.execute(text("""
            INSERT INTO progression_profiles (user_id, xp, level_name, status)
            VALUES (:user_id, 0, 'Beginner', 'Foundation')
            ON CONFLICT (user_id) DO NOTHING
        """), {"user_id": user_id})
        xp = 0
        streak = 0
    else:
        xp = int(row.xp or 0)
        streak = int(row.streak or 0)

    level_name = compute_level(score, xp)
    status = compute_status(score, plan)
    next_threshold = 1000 * (int(xp / 1000) + 1)

    conn.execute(text("""
        UPDATE progression_profiles
        SET level_name = :level_name,
            status = :status,
            last_seen_at = NOW(),
            updated_at = NOW()
        WHERE user_id = :user_id
    """), {
        "user_id": user_id,
        "level_name": level_name,
        "status": status,
    })

    return {
        "xp": xp,
        "streak": streak,
        "level": level_name,
        "status": status,
        "next_level_xp": next_threshold,
        "progress_percent": min(100, round((xp / next_threshold) * 100, 1)) if next_threshold else 0,
    }


def get_daily_briefing_loop(conn, user_id: int):
    ensure_product_tables(conn)

    today_rows = conn.execute(text("""
        SELECT action_key, status, xp_awarded, created_at
        FROM daily_briefing_actions
        WHERE user_id = :user_id
          AND created_at::date = CURRENT_DATE
        ORDER BY created_at DESC
    """), {"user_id": user_id}).fetchall()

    history_rows = conn.execute(text("""
        SELECT action_key, action_label, action_title, status, xp_awarded, created_at
        FROM daily_briefing_actions
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 10
    """), {"user_id": user_id}).fetchall()

    task_rows = conn.execute(text("""
        SELECT id, title, description, mission_key, priority, status, created_at, updated_at, completed_at
        FROM daily_action_tasks
        WHERE user_id = :user_id
        ORDER BY
            CASE
                WHEN status = 'todo' THEN 1
                WHEN status = 'in_progress' THEN 2
                WHEN status = 'done' THEN 3
                ELSE 4
            END,
            created_at DESC
        LIMIT 6
    """), {"user_id": user_id}).fetchall()

    today_actions = {}
    for row in today_rows:
        today_actions[row.action_key] = {
            "status": row.status,
            "xp_awarded": int(row.xp_awarded or 0),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    history = [
        {
            "action_key": row.action_key,
            "action_label": row.action_label,
            "action_title": row.action_title,
            "status": row.status,
            "xp_awarded": int(row.xp_awarded or 0),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in history_rows
    ]
    tasks = [
        {
            "id": int(row.id),
            "title": row.title,
            "description": row.description,
            "mission_key": row.mission_key,
            "priority": row.priority,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
        for row in task_rows
    ]
    done_tasks = [task for task in tasks if task.get("status") == "done"]
    open_tasks = [task for task in tasks if task.get("status") not in ("done", "cancelled")]
    xp_today = sum(int(action.get("xp_awarded") or 0) for action in today_actions.values())
    xp_recent = sum(int(action.get("xp_awarded") or 0) for action in history)

    return {
        "today_actions": today_actions,
        "history": history,
        "tasks": tasks,
        "summary": {
            "actions_today": len(today_actions),
            "actions_recent": len(history),
            "open_tasks": len(open_tasks),
            "done_tasks": len(done_tasks),
            "xp_today": xp_today,
            "xp_recent": xp_recent,
            "last_action": history[0] if history else None,
        },
    }


def attach_daily_briefing_loop(briefing: dict, loop: dict):
    if not briefing:
        return briefing

    today_actions = loop.get("today_actions") or {}
    briefing["daily_loop"] = loop
    briefing["actions"] = [
        {
            **action,
            "status": today_actions.get(action.get("key"), {}).get("status", action.get("status")),
            "xp_awarded": today_actions.get(action.get("key"), {}).get("xp_awarded", 0),
        }
        for action in briefing.get("actions", [])
    ]
    return briefing


def daily_action_status(action_key: str):
    return {
        "decide": "decided",
        "ignore": "ignored",
        "automate": "automation_requested",
    }.get(action_key)


def daily_action_xp(action_key: str):
    return {
        "decide": 20,
        "ignore": 0,
        "automate": 35,
    }.get(action_key, 0)


def academy_lesson_xp():
    return 15


def get_academy_progress(conn, user_id: int):
    ensure_product_tables(conn)

    rows = conn.execute(text("""
        SELECT lesson_key, module_key, status, xp_awarded, completed_at
        FROM academy_progress
        WHERE user_id = :user_id
        ORDER BY completed_at DESC
    """), {"user_id": user_id}).fetchall()

    completed = {}
    total_xp = 0
    for row in rows:
        total_xp += int(row.xp_awarded or 0)
        completed[row.lesson_key] = {
            "lesson_key": row.lesson_key,
            "module_key": row.module_key,
            "status": row.status,
            "xp_awarded": int(row.xp_awarded or 0),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }

    return {
        "completed": completed,
        "completed_lessons": len(completed),
        "xp_awarded": total_xp,
    }


def get_mission_progress(conn, user_id: int):
    ensure_product_tables(conn)

    rows = conn.execute(text("""
        SELECT mission_key, status, xp_awarded, completed_at
        FROM mission_progress
        WHERE user_id = :user_id
        ORDER BY completed_at DESC
    """), {"user_id": user_id}).fetchall()

    completed = {}
    for row in rows:
        completed[row.mission_key] = {
            "mission_key": row.mission_key,
            "status": row.status,
            "xp_awarded": int(row.xp_awarded or 0),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }

    return {"completed": completed}


def build_data_profile(conn, user_id: int):
    finance_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM finance_items WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    portfolio_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM portfolio WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    real_estate_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM real_estate_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    yield_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM yield_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    venture_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM venture_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    passion_assets_count = safe_count(
        conn,
        "SELECT COUNT(*) FROM passion_assets WHERE user_id = :user_id",
        {"user_id": user_id},
    )
    total_assets_count = portfolio_count + real_estate_count + yield_count + venture_count + passion_assets_count
    finance_income = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'revenus'",
        {"user_id": user_id},
    )
    finance_expenses = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'charges'",
        {"user_id": user_id},
    )
    finance_savings = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'epargne'",
        {"user_id": user_id},
    )
    finance_debt = safe_float(
        conn,
        "SELECT COALESCE(SUM(amount), 0) FROM finance_items WHERE user_id = :user_id AND type = 'dettes'",
        {"user_id": user_id},
    )
    onboarding_income = safe_float(
        conn,
        "SELECT COALESCE(revenus_mensuels, 0) FROM users WHERE id = :user_id",
        {"user_id": user_id},
    )
    onboarding_expenses = safe_float(
        conn,
        "SELECT COALESCE(charges_mensuelles, 0) FROM users WHERE id = :user_id",
        {"user_id": user_id},
    )
    monthly_income = finance_income or onboarding_income
    monthly_expenses = finance_expenses or onboarding_expenses
    cashflow_capacity = max(monthly_income - monthly_expenses, 0)
    savings_looks_monthly = (
        finance_savings > 0
        and monthly_income > 0
        and finance_savings <= max(cashflow_capacity * 1.2, monthly_income * 0.5, 1)
    )
    monthly_capacity = max(cashflow_capacity, finance_savings if savings_looks_monthly else 0)
    security_reserve = max(monthly_expenses * 12, 0)
    mobilizable_liquidity = max(finance_savings - security_reserve, 0)
    deployable_liquidity = mobilizable_liquidity * 0.35
    portfolio_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(quantity, 0) * COALESCE(purchase_price, 0)), 0)
        FROM portfolio
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    real_estate_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(NULLIF(estimated_value, 0), NULLIF(resale_price, 0), purchase_price, 0)), 0)
        FROM real_estate_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    yield_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(principal, 0) * (1 + (COALESCE(average_rate, 0) / 100) * (COALESCE(duration_months, 12) / 12.0))), 0)
        FROM yield_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    venture_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(
            CASE
                WHEN COALESCE(valuation, 0) > 0 THEN valuation
                ELSE GREATEST(COALESCE(revenue, 0) - COALESCE(charges, 0), 0)
                    + COALESCE(fundraising, 0)
                    - COALESCE(debts, 0)
            END
        ), 0)
        FROM venture_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    passion_assets_value = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(NULLIF(estimated_value, 0), acquisition_value, 0)), 0)
        FROM passion_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    passion_assets_cost = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(acquisition_value, 0)), 0)
        FROM passion_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    passion_assets_insured = safe_float(
        conn,
        """
        SELECT COALESCE(SUM(COALESCE(insured_value, 0)), 0)
        FROM passion_assets
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    business_value = yield_value + venture_value
    current_wealth = portfolio_value + real_estate_value + business_value + passion_assets_value
    projection_wealth = current_wealth + deployable_liquidity

    completed_steps = sum([
        finance_count > 0,
        portfolio_count > 0,
        real_estate_count > 0,
        yield_count > 0,
        venture_count > 0,
        passion_assets_count > 0,
    ])

    return {
        "finance_count": finance_count,
        "portfolio_count": portfolio_count,
        "real_estate_count": real_estate_count,
        "yield_count": yield_count,
        "venture_count": venture_count,
        "passion_assets_count": passion_assets_count,
        "total_assets_count": total_assets_count,
        "completed_steps": completed_steps,
        "completion_percent": round((completed_steps / 6) * 100),
        "monthly_income": round(monthly_income, 2),
        "monthly_expenses": round(monthly_expenses, 2),
        "monthly_savings": round(finance_savings, 2),
        "cashflow_capacity": round(cashflow_capacity, 2),
        "monthly_capacity": round(monthly_capacity, 2),
        "liquid_assets": round(finance_savings, 2),
        "security_reserve": round(security_reserve, 2),
        "mobilizable_liquidity": round(mobilizable_liquidity, 2),
        "deployable_liquidity": round(deployable_liquidity, 2),
        "debt_total": round(finance_debt, 2),
        "portfolio_value": round(portfolio_value, 2),
        "real_estate_value": round(real_estate_value, 2),
        "yield_value": round(yield_value, 2),
        "venture_value": round(venture_value, 2),
        "business_value": round(business_value, 2),
        "passion_assets_value": round(passion_assets_value, 2),
        "passion_assets_cost": round(passion_assets_cost, 2),
        "passion_assets_gain": round(passion_assets_value - passion_assets_cost, 2),
        "passion_assets_performance": round(((passion_assets_value - passion_assets_cost) / passion_assets_cost * 100) if passion_assets_cost > 0 else 0, 2),
        "passion_assets_insured": round(passion_assets_insured, 2),
        "current_wealth": round(current_wealth, 2),
        "projection_wealth": round(projection_wealth, 2),
    }


def build_modules(plan: str, score: int):
    visible = []
    locked = []

    for module in MODULE_REGISTRY:
        item = {
            **module,
            "required_plan": module["min_plan"],
            "required_score": module["min_score"],
        }

        if can_access_module(plan, score, module):
            visible.append({**item, "state": "active"})
        else:
            locked_item = {
                **item,
                "state": "discovery",
                "reason": (
                    "Profondeur limitee sur ton plan actuel"
                    if not plan_allows(plan, module["min_plan"])
                    else f"Score {module['min_score']} requis pour les analyses avancees"
                ),
            }
            visible.append(locked_item)
            locked.append(locked_item)

    return {"visible": visible, "locked": locked}


def build_missions(
    data_profile: dict,
    score: int,
    plan: str,
    academy_progress: dict | None = None,
    mission_progress: dict | None = None,
):
    missions = [
        {
            "key": "complete_finance",
            "title": "Completer ton cashflow",
            "description": "Ajoute revenus, charges, epargne et dettes pour clarifier tes fondations.",
            "xp": 100,
            "module": "finance",
        },
        {
            "key": "add_first_asset",
            "title": "Ajouter ton premier actif",
            "description": "C'est le premier pas vers une vision patrimoniale centralisee.",
            "xp": 120,
            "module": "portfolio",
        },
    ]
    completed_lessons = (academy_progress or {}).get("completed") or {}
    completed_missions = (mission_progress or {}).get("completed") or {}

    if score >= 45 and normalize_plan(plan) == "FREE":
        missions.append({
            "key": "unlock_growth",
            "title": "Debloquer la phase Growth",
            "description": "Ton profil commence a justifier diversification, immobilier et analytics.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "gold",
        })

    if score >= 70 and not plan_allows(plan, "ELITE"):
        missions.append({
            "key": "unlock_wealth_os",
            "title": "Passer en pilotage Wealth OS",
            "description": "Ton niveau devient compatible avec multi-user, gouvernance et guidance premium.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "elite",
        })

    if score >= 85 and not plan_allows(plan, "LIBERTY"):
        missions.append({
            "key": "unlock_liberty",
            "title": "Debloquer Liberty",
            "description": "Ton profil devient compatible avec une architecture patrimoniale souveraine.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "liberty",
        })

    if score >= 92 and not plan_allows(plan, "LEGACY"):
        missions.append({
            "key": "unlock_legacy",
            "title": "Preparer Legacy",
            "description": "Le vrai luxe est la stabilite: transmission, gouvernance et protection familiale.",
            "xp": 0,
            "module": "billing",
            "recommended_plan": "legacy",
        })

    def enrich_mission(mission: dict, index: int):
        key = mission.get("key")
        current_value = 0
        target_value = 1
        impact_dimension = "Pilotage"
        linked_daily_action = mission.get("description")
        academy_lesson = {
            "module_key": "family_office",
            "module_title": "Family Office",
            "lesson_key": "weekly_board",
            "lesson_title": "Organiser une decision patrimoniale",
            "duration": "7 min",
            "reason": "Cette lecon aide a transformer une lecture White Rock en decision suivie.",
        }

        if key == "complete_finance":
            current_value = data_profile.get("finance_count", 0)
            target_value = 1
            impact_dimension = "Cashflow"
            linked_daily_action = "Ajouter au moins une ligne de revenu, charge, epargne ou dette pour rendre le cashflow lisible."
            academy_lesson = {
                "module_key": "foundations",
                "module_title": "Fondations",
                "lesson_key": "cashflow",
                "lesson_title": "Lire son cashflow",
                "duration": "6 min",
                "reason": "Comprendre les flux rend la mission finance plus concrete et mesurable.",
            }
        elif key == "add_first_asset":
            current_value = data_profile.get("portfolio_count", 0)
            target_value = 1
            impact_dimension = "Allocation"
            linked_daily_action = "Ajouter un actif financier pour commencer a mesurer l'exposition et la performance."
            academy_lesson = {
                "module_key": "investing",
                "module_title": "Investissement",
                "lesson_key": "first_asset",
                "lesson_title": "Ajouter son premier actif",
                "duration": "5 min",
                "reason": "La mission devient plus simple quand l'utilisateur comprend ce qu'une ligne d'actif apporte au cockpit.",
            }
        elif key == "unlock_growth":
            current_value = score
            target_value = 45
            impact_dimension = "Croissance"
            linked_daily_action = "Comparer la valeur des leviers Growth avec ton score et tes donnees deja renseignees."
            academy_lesson = {
                "module_key": "investing",
                "module_title": "Investissement",
                "lesson_key": "allocation",
                "lesson_title": "Comprendre l'allocation",
                "duration": "8 min",
                "reason": "Growth devient utile quand les poches patrimoniales ont chacune un role clair.",
            }
        elif key == "unlock_wealth_os":
            current_value = score
            target_value = 70
            impact_dimension = "Gouvernance"
            linked_daily_action = "Verifier si le pilotage avance devient utile au regard de ton score et de tes actifs suivis."
            academy_lesson = {
                "module_key": "family_office",
                "module_title": "Family Office",
                "lesson_key": "weekly_board",
                "lesson_title": "Organiser une decision patrimoniale",
                "duration": "7 min",
                "reason": "Le pilotage Wealth OS doit deboucher sur des arbitrages suivis, pas seulement sur des scores.",
            }
        elif key == "unlock_liberty":
            current_value = score
            target_value = 85
            impact_dimension = "Souverainete"
            linked_daily_action = "Evaluer les besoins de controle, transmission et arbitrage avances."
            academy_lesson = {
                "module_key": "family_office",
                "module_title": "Family Office",
                "lesson_key": "transmission_basics",
                "lesson_title": "Bases de transmission",
                "duration": "9 min",
                "reason": "Liberty suppose une vision plus claire du controle, de la protection et de la continuite.",
            }
        elif key == "unlock_legacy":
            current_value = score
            target_value = 92
            impact_dimension = "Transmission"
            linked_daily_action = "Clarifier les enjeux familiaux, de protection et de patrimoine transmissible."
            academy_lesson = {
                "module_key": "family_office",
                "module_title": "Family Office",
                "lesson_key": "transmission_basics",
                "lesson_title": "Bases de transmission",
                "duration": "9 min",
                "reason": "Legacy doit etre compris comme une architecture familiale durable, pas comme un simple niveau premium.",
            }

        progress_percent = (
            min(100, round((float(current_value or 0) / float(target_value or 1)) * 100, 1))
            if target_value
            else 0
        )
        lesson_progress = completed_lessons.get(academy_lesson["lesson_key"])
        mission_done = completed_missions.get(key)
        computed_status = "completed" if mission_done else "ready" if progress_percent >= 100 else "pending"
        academy_lesson = {
            **academy_lesson,
            "completed": bool(lesson_progress),
            "completed_at": lesson_progress.get("completed_at") if lesson_progress else None,
            "xp_awarded": int(lesson_progress.get("xp_awarded") or 0) if lesson_progress else 0,
        }

        return {
            **mission,
            "current_value": round(float(current_value or 0), 2),
            "target_value": round(float(target_value or 0), 2),
            "progress_percent": progress_percent,
            "impact_dimension": impact_dimension,
            "linked_daily_action": linked_daily_action,
            "linked_academy_lesson": academy_lesson,
            "is_priority": index == 0,
            "completed": bool(mission_done),
            "completed_at": mission_done.get("completed_at") if mission_done else None,
            "xp_awarded": int(mission_done.get("xp_awarded") or 0) if mission_done else 0,
            "status": mission.get("status") or computed_status,
        }

    return [enrich_mission(mission, index) for index, mission in enumerate(missions[:3])]


def build_wealth_academy(
    data_profile: dict,
    missions: list[dict],
    score: int,
    plan: str,
    academy_progress: dict | None = None,
):
    modules = [
        {
            "key": "foundations",
            "title": "Fondations",
            "description": "Cashflow, fonds d'urgence, dettes et patrimoine net.",
            "lessons": [
                {
                    "key": "cashflow",
                    "title": "Lire son cashflow",
                    "duration": "6 min",
                    "outcome": "Comprendre ce qui entre, ce qui sort et ce qui peut etre deploye.",
                },
                {
                    "key": "emergency_fund",
                    "title": "Construire un fonds d'urgence",
                    "duration": "7 min",
                    "outcome": "Transformer la liquidite en marge de securite mesurable.",
                },
                {
                    "key": "debt_weight",
                    "title": "Mesurer le poids des dettes",
                    "duration": "5 min",
                    "outcome": "Identifier si la dette freine ou accelere la trajectoire.",
                },
            ],
        },
        {
            "key": "investing",
            "title": "Investissement",
            "description": "Allocation, diversification, risque et horizon.",
            "lessons": [
                {
                    "key": "first_asset",
                    "title": "Ajouter son premier actif",
                    "duration": "5 min",
                    "outcome": "Commencer a suivre exposition, performance et poids relatif.",
                },
                {
                    "key": "allocation",
                    "title": "Comprendre l'allocation",
                    "duration": "8 min",
                    "outcome": "Relier chaque actif a un role clair dans le patrimoine.",
                },
                {
                    "key": "risk_horizon",
                    "title": "Risque et horizon",
                    "duration": "7 min",
                    "outcome": "Eviter les decisions incompatibles avec son temps disponible.",
                },
            ],
        },
        {
            "key": "real_estate",
            "title": "Immobilier",
            "description": "Valeur, dette, rendement et cashflow locatif.",
            "lessons": [
                {
                    "key": "property_value",
                    "title": "Lire la valeur d'un bien",
                    "duration": "6 min",
                    "outcome": "Comparer valeur estimee, prix d'achat et plus-value latente.",
                },
                {
                    "key": "rental_yield",
                    "title": "Comprendre le rendement locatif",
                    "duration": "7 min",
                    "outcome": "Ne pas confondre rendement brut, charges et flux reel.",
                },
            ],
        },
        {
            "key": "business",
            "title": "Business",
            "description": "Revenus, charges, marge et valorisation.",
            "lessons": [
                {
                    "key": "business_margin",
                    "title": "Lire une marge operationnelle",
                    "duration": "6 min",
                    "outcome": "Savoir si l'activite cree de la valeur ou absorbe du cash.",
                },
                {
                    "key": "business_value",
                    "title": "Suivre une valeur business",
                    "duration": "8 min",
                    "outcome": "Passer d'une activite suivie a un actif patrimonial lisible.",
                },
            ],
        },
        {
            "key": "family_office",
            "title": "Family Office",
            "description": "Gouvernance, transmission, documentation et pilotage.",
            "lessons": [
                {
                    "key": "weekly_board",
                    "title": "Organiser une decision patrimoniale",
                    "duration": "7 min",
                    "outcome": "Transformer une lecture en decision, puis en action suivie.",
                },
                {
                    "key": "transmission_basics",
                    "title": "Bases de transmission",
                    "duration": "9 min",
                    "outcome": "Identifier les informations a documenter avant toute strategie avancee.",
                },
            ],
        },
    ]

    mission = missions[0] if missions else None
    finance_count = int(data_profile.get("finance_count") or 0)
    portfolio_count = int(data_profile.get("portfolio_count") or 0)
    real_estate_count = int(data_profile.get("real_estate_count") or 0)
    venture_count = int(data_profile.get("venture_count") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)

    recommended_module = "family_office"
    recommended_lesson = "weekly_board"
    why_now = "La boucle quotidienne est active: apprendre a transformer une decision en action suivie renforce le pilotage."

    if finance_count == 0:
        recommended_module = "foundations"
        recommended_lesson = "cashflow"
        why_now = "Le backend ne voit pas encore assez de donnees de revenus, charges, epargne ou dettes."
    elif debt_total > 0:
        recommended_module = "foundations"
        recommended_lesson = "debt_weight"
        why_now = "Une dette suivie existe: comprendre son poids rend la trajectoire plus realiste."
    elif portfolio_count == 0:
        recommended_module = "investing"
        recommended_lesson = "first_asset"
        why_now = "Aucun actif financier n'est encore suivi: la premiere ligne rend l'allocation mesurable."
    elif monthly_capacity > 0:
        recommended_module = "investing"
        recommended_lesson = "allocation"
        why_now = "Une capacite mensuelle existe: l'allocation aide a transformer cette marge en trajectoire."
    elif real_estate_count > 0:
        recommended_module = "real_estate"
        recommended_lesson = "property_value"
        why_now = "Une poche immobiliere existe: relire valeur et rendement clarifie le patrimoine visible."
    elif venture_count > 0:
        recommended_module = "business"
        recommended_lesson = "business_margin"
        why_now = "Une poche business existe: la marge dit si elle cree vraiment de la valeur."

    if mission and mission.get("key") == "complete_finance":
        recommended_module = "foundations"
        recommended_lesson = "cashflow"
    elif mission and mission.get("key") == "add_first_asset":
        recommended_module = "investing"
        recommended_lesson = "first_asset"

    lesson_content = {
        "cashflow": {
            "reading": "Le cashflow est la difference entre ce qui entre chaque mois et ce qui sort. Dans White Rock, il sert a savoir si la trajectoire peut accelerer sans fragiliser la securite.",
            "key_points": [
                "Un cashflow positif cree une capacite d'action mensuelle.",
                "Un cashflow negatif demande d'abord de comprendre les charges.",
                "La qualite des projections depend de revenus et charges bien renseignes.",
            ],
            "exercise": "Verifie que tes revenus et charges principales sont bien presents dans la page Finances.",
            "action_steps": [
                "Ajouter au moins un revenu mensuel.",
                "Ajouter les charges fixes principales.",
                "Relire le cashflow mensuel dans White Rock Center.",
            ],
        },
        "emergency_fund": {
            "reading": "Le fonds d'urgence protege la trajectoire. Il evite de vendre un actif ou de s'endetter pour absorber un imprevu.",
            "key_points": [
                "La reserve se mesure en mois de charges.",
                "Une reserve trop faible rend l'investissement plus stressant.",
                "Une reserve trop elevee peut aussi laisser du capital dormir.",
            ],
            "exercise": "Compare ton epargne disponible avec 3 a 6 mois de charges mensuelles.",
            "action_steps": [
                "Identifier les charges mensuelles essentielles.",
                "Calculer 3 mois de securite.",
                "Decider si la reserve doit etre renforcee ou partiellement mobilisee.",
            ],
        },
        "debt_weight": {
            "reading": "La dette n'est pas toujours mauvaise. Elle devient un probleme quand elle absorbe trop de revenus ou reduit la marge de manoeuvre.",
            "key_points": [
                "Le ratio dette / revenus aide a mesurer la pression.",
                "Une dette productive finance un actif ou une capacite future.",
                "Une dette de consommation doit etre surveillee plus strictement.",
            ],
            "exercise": "Regarde le poids total des dettes face a tes revenus mensuels.",
            "action_steps": [
                "Verifier les dettes renseignees.",
                "Identifier la dette la plus lourde.",
                "Choisir entre remboursement prioritaire ou simple surveillance.",
            ],
        },
        "first_asset": {
            "reading": "Ajouter un premier actif transforme le patrimoine en portefeuille lisible. Meme une seule ligne permet de suivre exposition, valeur et performance.",
            "key_points": [
                "Un actif renseigne donne un point de depart mesurable.",
                "La valeur actuelle permet de distinguer patrimoine et cout d'achat.",
                "La categorie de l'actif aide a lire la concentration.",
            ],
            "exercise": "Ajoute l'actif financier le plus important ou le plus representatif.",
            "action_steps": [
                "Choisir une action, ETF, crypto ou autre actif suivi.",
                "Renseigner quantite et prix d'achat.",
                "Relire l'exposition dominante dans Investissements.",
            ],
        },
        "allocation": {
            "reading": "L'allocation repond a une question simple: quel role joue chaque poche dans ton patrimoine ? Securite, croissance, rendement ou option future.",
            "key_points": [
                "Une allocation lisible reduit les decisions impulsives.",
                "La concentration n'est pas toujours mauvaise, mais elle doit etre consciente.",
                "La capacite mensuelle doit aller vers un role prioritaire.",
            ],
            "exercise": "Associe chaque grande poche patrimoniale a un role clair.",
            "action_steps": [
                "Identifier la poche dominante.",
                "Verifier si elle correspond a ton objectif.",
                "Choisir la poche a renforcer en premier.",
            ],
        },
        "risk_horizon": {
            "reading": "Le risque depend du temps disponible. Un actif volatil peut etre acceptable a long terme et dangereux a court terme.",
            "key_points": [
                "Plus l'horizon est court, plus la liquidite compte.",
                "Plus l'horizon est long, plus la volatilite peut etre absorbee.",
                "Un objectif familial ou immobilier demande une marge de securite.",
            ],
            "exercise": "Classe ton objectif principal en horizon court, moyen ou long.",
            "action_steps": [
                "Choisir l'objectif prioritaire.",
                "Associer un horizon de temps.",
                "Verifier si les actifs actuels sont coherents avec cet horizon.",
            ],
        },
        "property_value": {
            "reading": "La valeur immobiliere utile n'est pas seulement le prix d'achat. White Rock compare cout, valeur estimee et plus-value latente.",
            "key_points": [
                "La valeur estimee donne une photo actuelle.",
                "La plus-value latente reste theorique tant que le bien n'est pas vendu.",
                "L'immobilier peut dominer fortement le patrimoine visible.",
            ],
            "exercise": "Verifie que chaque bien a une valeur estimee realiste.",
            "action_steps": [
                "Mettre a jour la valeur estimee.",
                "Comparer avec le prix d'achat.",
                "Relire le poids immobilier dans Patrimoine.",
            ],
        },
        "rental_yield": {
            "reading": "Le rendement locatif doit etre lu apres charges. Un bien peut prendre de la valeur mais produire peu de cashflow.",
            "key_points": [
                "Le loyer seul ne suffit pas a mesurer la performance.",
                "Les charges reduisent le rendement reel.",
                "Un rendement faible peut rester acceptable si la strategie est patrimoniale.",
            ],
            "exercise": "Compare loyer, charges et valeur du bien.",
            "action_steps": [
                "Renseigner le loyer mensuel.",
                "Renseigner les charges mensuelles.",
                "Lire le rendement locatif dans Immobilier.",
            ],
        },
        "business_margin": {
            "reading": "Une activite business devient patrimoniale quand elle cree une marge suivie. Le chiffre d'affaires seul ne suffit pas.",
            "key_points": [
                "La marge mesure ce qui reste apres charges.",
                "Une activite negative peut etre une phase d'investissement ou un signal de vigilance.",
                "La performance operationnelle passe avant la complexite.",
            ],
            "exercise": "Compare chiffre d'affaires, charges et resultat suivi.",
            "action_steps": [
                "Verifier le chiffre d'affaires renseigne.",
                "Verifier les charges business.",
                "Identifier une action pour ameliorer la marge.",
            ],
        },
        "business_value": {
            "reading": "La valeur business depend de la capacite a transformer une activite en actif: revenus, marge, systematisation et potentiel.",
            "key_points": [
                "Une valorisation doit rester prudente si la marge est faible.",
                "La systematisation augmente la valeur potentielle.",
                "Un business suivi devient un bloc patrimonial distinct.",
            ],
            "exercise": "Relis si le business cree de la valeur ou consomme du cash.",
            "action_steps": [
                "Verifier revenus, charges et valeur suivie.",
                "Identifier le levier operationnel principal.",
                "Mettre a jour la valeur si elle est justifiee.",
            ],
        },
        "weekly_board": {
            "reading": "Une decision patrimoniale utile doit etre simple, suivie et relue. Le Family Office ne multiplie pas les idees: il priorise.",
            "key_points": [
                "Une bonne decision tient en une action concrete.",
                "La priorite vient des donnees, pas de l'envie du moment.",
                "Le suivi evite d'oublier les arbitrages choisis.",
            ],
            "exercise": "Choisis une seule action a suivre cette semaine.",
            "action_steps": [
                "Lire l'action prioritaire du CEO Daily Briefing.",
                "Decider, ignorer ou automatiser.",
                "Revenir dans Progression pour verifier le suivi.",
            ],
        },
        "transmission_basics": {
            "reading": "La transmission commence par la clarte: qui doit comprendre quoi, quels documents existent, et quelles decisions doivent survivre au temps.",
            "key_points": [
                "La gouvernance familiale reduit l'ambiguite.",
                "Les documents importants doivent etre identifies avant l'urgence.",
                "Legacy concerne la continuite, pas seulement le niveau de patrimoine.",
            ],
            "exercise": "Liste les informations qui seraient utiles a un proche ou conseiller en cas d'imprevu.",
            "action_steps": [
                "Identifier documents importants.",
                "Clarifier les personnes concernees.",
                "Noter le premier point de gouvernance a structurer.",
            ],
        },
    }

    for module in modules:
        for module_lesson in module.get("lessons") or []:
            module_lesson.update(lesson_content.get(module_lesson["key"], {}))

    progress = academy_progress or {"completed": {}, "completed_lessons": 0, "xp_awarded": 0}
    completed = progress.get("completed") or {}
    total_lessons = 0

    for module in modules:
        completed_count = 0
        lessons = module.get("lessons") or []
        total_lessons += len(lessons)

        for module_lesson in lessons:
            lesson_progress = completed.get(module_lesson["key"])
            module_lesson["completed"] = bool(lesson_progress)
            module_lesson["completed_at"] = lesson_progress.get("completed_at") if lesson_progress else None
            module_lesson["xp_awarded"] = int(lesson_progress.get("xp_awarded") or 0) if lesson_progress else 0
            if lesson_progress:
                completed_count += 1

        module["lesson_count"] = len(lessons)
        module["completed_count"] = completed_count
        module["progress_percent"] = (
            round((completed_count / len(lessons)) * 100, 1)
            if lessons
            else 0
        )

    selected_module = next((item for item in modules if item["key"] == recommended_module), modules[0])
    lesson = next(
        (item for item in selected_module["lessons"] if item["key"] == recommended_lesson),
        selected_module["lessons"][0],
    )
    completed_lessons = int(progress.get("completed_lessons") or 0)

    return {
        "title": "Wealth Academy",
        "plan": plan,
        "score": score,
        "progress": {
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "progress_percent": round((completed_lessons / total_lessons) * 100, 1) if total_lessons else 0,
            "xp_awarded": int(progress.get("xp_awarded") or 0),
        },
        "recommended": {
            "module_key": selected_module["key"],
            "module_title": selected_module["title"],
            "lesson_key": lesson["key"],
            "lesson_title": lesson["title"],
            "duration": lesson["duration"],
            "outcome": lesson["outcome"],
            "reading": lesson.get("reading"),
            "key_points": lesson.get("key_points") or [],
            "exercise": lesson.get("exercise"),
            "action_steps": lesson.get("action_steps") or [],
            "why_now": why_now,
            "linked_mission_key": mission.get("key") if mission else None,
            "linked_mission_title": mission.get("title") if mission else None,
            "completed": bool(lesson.get("completed")),
            "completed_at": lesson.get("completed_at"),
            "xp_awarded": int(lesson.get("xp_awarded") or 0),
        },
        "modules": modules,
    }


def build_strategic_brief(data_profile: dict, score: int, plan: str):
    normalized = normalize_plan(plan)
    portfolio_count = data_profile.get("portfolio_count", 0)
    finance_count = data_profile.get("finance_count", 0)
    total_assets = data_profile.get("total_assets_count", 0)

    if finance_count == 0:
        priority = "Completer le contexte financier"
        action = "Donnee manquante: revenu ou charge a renseigner."
    elif portfolio_count == 0:
        priority = "Creer la premiere ligne patrimoniale mesurable"
        action = "Donnee manquante: actif financier a renseigner."
    elif data_profile.get("monthly_capacity", 0) > 0:
        priority = "Transformer la capacite mensuelle en trajectoire"
        action = "Signal disponible: capacite mensuelle et patrimoine peuvent etre projetes."
    else:
        priority = "Qualifier le prochain signal utile"
        action = "Signal disponible: objectifs, temps et risque peuvent etre compares par Ethan."

    if plan_allows(normalized, "LEGACY"):
        opportunity = "Signal familial: gouvernance ou transmission a structurer."
        risk = "Signal de vigilance: roles familiaux incomplets."
    elif plan_allows(normalized, "LIBERTY"):
        opportunity = "Signal de profondeur: scenario patrimonial 12 mois disponible."
        risk = "Signal de vigilance: intention patrimoniale a expliciter."
    elif plan_allows(normalized, "GOLD"):
        opportunity = "Signal produit: contexte portefeuille et objectifs disponibles pour Ethan."
        risk = "Signal de vigilance: concentration a mesurer."
    else:
        opportunity = "Signal produit: base de donnees a enrichir."
        risk = "Signal de vigilance: contexte encore incomplet."

    return {
        "priority": priority,
        "main_lever": f"{total_assets} asset(s) suivis, {data_profile.get('completion_percent', 0)}% de completion.",
        "main_risk": risk,
        "opportunity": opportunity,
        "next_action": action,
    }


def build_future_view(data_profile: dict, score: int, plan: str):
    normalized = normalize_plan(plan)
    current_wealth = float(data_profile.get("projection_wealth") or data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    deployable_liquidity = float(data_profile.get("deployable_liquidity") or 0)

    if plan_allows(normalized, "LIBERTY"):
        annual_return = 0.055
    elif plan_allows(normalized, "GOLD"):
        annual_return = 0.045
    else:
        annual_return = 0.035

    if score >= 70:
        annual_return += 0.005
    elif score < 35:
        annual_return -= 0.005

    annual_contribution = max(monthly_capacity, 0) * 12

    def project(years: int):
        value = current_wealth
        for _ in range(years):
            value = value * (1 + annual_return) + annual_contribution
        return round(value, 2)

    if current_wealth > 0 and monthly_capacity > 0:
        confidence = "solid"
        assumption = "Projection prudente: patrimoine suivi, capacite mensuelle reelle et part mobilisable de liquidite apres reserve de securite."
    elif current_wealth > 0:
        confidence = "asset_based"
        assumption = "Projection prudente: patrimoine suivi et liquidite mobilisable, sans capacite mensuelle exploitable."
    else:
        confidence = "data_light"
        assumption = "Projection backend limitee: ajoute revenus, charges et actifs pour rendre le futur lisible."

    return {
        "title": "Future View",
        "current_wealth": round(current_wealth, 2),
        "monthly_capacity": round(monthly_capacity, 2),
        "deployable_liquidity": round(deployable_liquidity, 2),
        "annual_return": round(annual_return * 100, 2),
        "confidence": confidence,
        "assumption": assumption,
        "scenarios": [
            {"label": "3 ans", "years": 3, "value": project(3)},
            {"label": "5 ans", "years": 5, "value": project(5)},
            {"label": "10 ans", "years": 10, "value": project(10)},
        ],
    }


MONTH_LABELS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]


def add_months(base_date: date, months: int):
    month_index = base_date.month - 1 + max(months, 0)
    year = base_date.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def estimate_months_to_target(current_wealth: float, monthly_capacity: float, annual_return: float, target: float):
    if target <= current_wealth:
        return 0
    if monthly_capacity <= 0 and current_wealth <= 0:
        return None
    value = current_wealth
    monthly_return = (1 + annual_return) ** (1 / 12) - 1
    for month in range(1, 481):
        value = value * (1 + monthly_return) + max(monthly_capacity, 0)
        if value >= target:
            return month
    return None


def format_month_label(target_date: date):
    return f"{MONTH_LABELS[target_date.month - 1]} {target_date.year}"


def build_wealth_timeline(data_profile: dict, future_view: dict | None = None):
    current_wealth = float(data_profile.get("projection_wealth") or data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    annual_return = float((future_view or {}).get("annual_return") or 4.5) / 100
    today = date.today()
    stages = [
        ("Aujourd'hui", 0),
        ("100k", 100000),
        ("250k", 250000),
        ("500k", 500000),
        ("1M", 1000000),
        ("Liberte financiere", 1500000),
    ]
    timeline = []
    next_stage = None

    for label, target in stages:
        if target == 0:
            status = "current"
            progress = 100
            months_to_target = 0
            estimated_date = today.isoformat()
            estimated_label = "Aujourd'hui"
        else:
            status = "achieved" if current_wealth >= target else "locked"
            progress = min(100, round((current_wealth / target) * 100, 1)) if target else 100
            months_to_target = estimate_months_to_target(current_wealth, monthly_capacity, annual_return, float(target))
            if months_to_target is None:
                estimated_date = None
                estimated_label = "Date a confirmer"
            elif months_to_target == 0:
                estimated_date = today.isoformat()
                estimated_label = "Franchi"
            else:
                target_date = add_months(today, months_to_target)
                estimated_date = target_date.isoformat()
                estimated_label = format_month_label(target_date)
            if status == "locked" and next_stage is None:
                next_stage = {
                    "label": label,
                    "target": target,
                    "months_to_target": months_to_target,
                    "estimated_date": estimated_date,
                    "estimated_label": estimated_label,
                }

        timeline.append({
            "label": label,
            "target": target,
            "status": status,
            "progress_percent": progress,
            "distance_remaining": max(round(target - current_wealth, 2), 0) if target else 0,
            "months_to_target": months_to_target,
            "estimated_date": estimated_date,
            "estimated_label": estimated_label,
        })

    return {
        "current_wealth": round(current_wealth, 2),
        "monthly_velocity": round(monthly_capacity, 2),
        "progress_percent": min(100, round((current_wealth / 1000000) * 100, 1)) if current_wealth else 0,
        "next_milestone": next_stage,
        "stages": timeline,
    }


def build_mission_control(strategic_brief: dict, missions: list[dict], future_view: dict):
    mission = next((item for item in missions if not item.get("completed")), None)
    if not mission and missions:
        mission = missions[0]

    return {
        "risk": {
            "title": "Risque principal",
            "description": strategic_brief.get("main_risk"),
        },
        "opportunity": {
            "title": "Opportunite",
            "description": strategic_brief.get("opportunity"),
        },
        "decision": {
            "title": "Decision du moment",
            "description": strategic_brief.get("priority"),
            "action": strategic_brief.get("next_action"),
        },
        "mission": {
            "title": mission.get("title") if mission else "Contexte a enrichir",
            "description": mission.get("description") if mission else "Ajoute une donnee utile pour activer une mission verifiable.",
            "status": mission.get("status") if mission else "pending",
            "xp": mission.get("xp") if mission else 0,
        },
        "future_signal": {
            "title": "Projection",
            "description": future_view.get("assumption"),
            "confidence": future_view.get("confidence"),
        },
    }


def build_family_office_view(data_profile: dict, plan: str):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    allocation = [
        {
            "key": "investments",
            "label": "Investissements",
            "value": round(float(data_profile.get("portfolio_value") or 0), 2),
            "description": "Actifs financiers suivis par le portefeuille backend.",
        },
        {
            "key": "real_estate",
            "label": "Immobilier",
            "value": round(float(data_profile.get("real_estate_value") or 0), 2),
            "description": "Valeur estimee des biens immobiliers suivis.",
        },
        {
            "key": "business",
            "label": "Business",
            "value": round(float(data_profile.get("business_value") or 0), 2),
            "description": "Yield assets, private equity et activites valorisees.",
        },
        {
            "key": "passion_assets",
            "label": "Passion Assets",
            "value": round(float(data_profile.get("passion_assets_value") or 0), 2),
            "description": "Art, montres, voitures, vins, bijoux et collections declarees.",
        },
    ]
    active_domains = sum(1 for item in allocation if item["value"] > 0)
    summary = (
        "Lecture globale active: le patrimoine est consolide par domaines."
        if current_wealth > 0
        else "Lecture globale prete: ajoute actifs, immobilier ou business pour activer la valeur."
    )

    return {
        "title": "Family Office Mode",
        "summary": summary,
        "global_wealth": round(current_wealth, 2),
        "active_domains": active_domains,
        "plan": normalize_plan(plan),
        "allocation": allocation,
    }


def build_wealth_gps(data_profile: dict, future_view: dict):
    current_wealth = float(data_profile.get("projection_wealth") or data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    next_milestone = next(
        (item for item in [100000, 250000, 500000, 1000000] if current_wealth < item),
        1500000,
    )
    routes = [
        {
            "key": "markets",
            "label": "Marches financiers",
            "annual_return": 0.055,
            "monthly_multiplier": 1,
            "description": "Trajectoire liquide basee sur la capacite mensuelle et le portefeuille financier.",
        },
        {
            "key": "real_estate",
            "label": "Immobilier",
            "annual_return": 0.045,
            "monthly_multiplier": 1.1,
            "description": "Trajectoire patrimoniale avec effet capital long terme et effort d'epargne plus structure.",
        },
        {
            "key": "business",
            "label": "Business",
            "annual_return": 0.075,
            "monthly_multiplier": 1.2,
            "description": "Trajectoire orientee creation de valeur via activite, expertise ou revenus semi-recurrents.",
        },
        {
            "key": "balanced",
            "label": "Mix equilibre",
            "annual_return": 0.06,
            "monthly_multiplier": 1.05,
            "description": "Trajectoire hybride entre liquidite, croissance et diversification progressive.",
        },
    ]

    def project_route(route: dict, years: int):
        value = current_wealth
        annual_contribution = monthly_capacity * float(route["monthly_multiplier"]) * 12
        for _ in range(years):
            value = value * (1 + float(route["annual_return"])) + annual_contribution
        return round(value, 2)

    enriched_routes = []
    for route in routes:
        years_to_next = None
        if next_milestone > current_wealth:
            value = current_wealth
            annual_contribution = monthly_capacity * float(route["monthly_multiplier"]) * 12
            for year in range(1, 31):
                value = value * (1 + float(route["annual_return"])) + annual_contribution
                if value >= next_milestone:
                    years_to_next = year
                    break

        enriched_routes.append({
            **route,
            "annual_return": round(float(route["annual_return"]) * 100, 2),
            "value_10y": project_route(route, 10),
            "years_to_next_milestone": years_to_next,
        })

    return {
        "title": "GPS patrimonial",
        "current_position": round(current_wealth, 2),
        "next_destination": next_milestone,
        "assumption": future_view.get("assumption"),
        "routes": enriched_routes,
    }


def build_digital_twin(data_profile: dict):
    current_wealth = float(data_profile.get("projection_wealth") or data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    scenarios = [
        {
            "key": "invest_500",
            "label": "Investir 500 EUR/mois",
            "monthly_delta": 500,
            "annual_return": 0.055,
            "description": "Simulation d'une discipline d'investissement mensuelle fixe.",
        },
        {
            "key": "business_plus",
            "label": "Developper un revenu business",
            "monthly_delta": 750,
            "annual_return": 0.06,
            "description": "Simulation d'un surplus mensuel cree par activite ou offre recurrente.",
        },
        {
            "key": "keep_current",
            "label": "Continuer au rythme actuel",
            "monthly_delta": 0,
            "annual_return": 0.045,
            "description": "Simulation de reference avec les donnees deja presentes dans le backend.",
        },
    ]

    def simulate(monthly_delta: float, annual_return: float, years: int):
        value = current_wealth
        annual_contribution = max(monthly_capacity + monthly_delta, 0) * 12
        for _ in range(years):
            value = value * (1 + annual_return) + annual_contribution
        return round(value, 2)

    return {
        "title": "Double patrimonial",
        "basis": "Simulations backend hypothetiques, sans remplacer Ethan ni une decision personnelle.",
        "scenarios": [
            {
                **scenario,
                "annual_return": round(float(scenario["annual_return"]) * 100, 2),
                "value_5y": simulate(float(scenario["monthly_delta"]), float(scenario["annual_return"]), 5),
                "value_10y": simulate(float(scenario["monthly_delta"]), float(scenario["annual_return"]), 10),
            }
            for scenario in scenarios
        ],
    }


def build_weak_signals(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    allocation = {
        "investments": float(data_profile.get("portfolio_value") or 0),
        "real_estate": float(data_profile.get("real_estate_value") or 0),
        "business": float(data_profile.get("business_value") or 0),
        "passion_assets": float(data_profile.get("passion_assets_value") or 0),
    }
    signals = []

    if data_profile.get("completion_percent", 0) < 60:
        signals.append({
            "type": "data_depth",
            "title": "Contexte incomplet",
            "description": "Le cockpit manque encore de donnees pour lire toute la trajectoire.",
            "severity": "medium",
        })
    if monthly_capacity <= 0 and (data_profile.get("monthly_income", 0) or data_profile.get("monthly_expenses", 0)):
        signals.append({
            "type": "capacity",
            "title": "Capacite mensuelle fragile",
            "description": "Les donnees backend ne montrent pas encore de marge mensuelle exploitable.",
            "severity": "high",
        })
    if current_wealth > 0:
        main_domain, main_value = max(allocation.items(), key=lambda item: item[1])
        if main_value / current_wealth >= 0.7:
            labels = {"investments": "investissements", "real_estate": "immobilier", "business": "business", "passion_assets": "Passion Assets"}
            signals.append({
                "type": "concentration",
                "title": "Concentration patrimoniale",
                "description": f"Le domaine {labels.get(main_domain, main_domain)} porte une grande partie de la valeur suivie.",
                "severity": "medium",
            })
    if not signals:
        signals.append({
            "type": "stability",
            "title": "Aucun signal critique",
            "description": "Les donnees disponibles ne font pas ressortir de fragilite immediate.",
            "severity": "low",
        })

    return {
        "title": "Signaux faibles",
        "signals": signals[:4],
    }


def build_self_benchmark(conn, user_id: int, data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    value_6m = safe_float(
        conn,
        """
        SELECT total_value
        FROM portfolio_history
        WHERE user_id = :user_id AND created_at <= NOW() - INTERVAL '6 months'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    value_12m = safe_float(
        conn,
        """
        SELECT total_value
        FROM portfolio_history
        WHERE user_id = :user_id AND created_at <= NOW() - INTERVAL '12 months'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"user_id": user_id},
    )

    def delta(previous: float):
        if previous <= 0:
            return None
        return {
            "previous_value": round(previous, 2),
            "delta_value": round(current_wealth - previous, 2),
            "delta_percent": round(((current_wealth - previous) / previous) * 100, 1),
        }

    return {
        "title": "Classement contre toi-meme",
        "current_wealth": round(current_wealth, 2),
        "six_months": delta(value_6m),
        "twelve_months": delta(value_12m),
        "basis": "Comparaison backend avec l'historique portfolio disponible.",
    }


def build_wealth_story(data_profile: dict, progression: dict):
    events = [
        {
            "label": "Aujourd'hui",
            "title": "Point de depart patrimonial",
            "description": f"{round(float(data_profile.get('current_wealth') or 0), 2)} EUR suivis dans White Rock.",
        },
        {
            "label": "Progression",
            "title": progression.get("level") or "Builder",
            "description": f"{progression.get('xp', 0)} XP et {data_profile.get('completion_percent', 0)}% de contexte complete.",
        },
    ]
    if data_profile.get("portfolio_count", 0) > 0:
        events.append({
            "label": "Investissements",
            "title": "Portefeuille active",
            "description": f"{data_profile.get('portfolio_count', 0)} ligne(s) financiere(s) suivie(s).",
        })
    if data_profile.get("real_estate_count", 0) > 0:
        events.append({
            "label": "Immobilier",
            "title": "Brique immobiliere",
            "description": f"{data_profile.get('real_estate_count', 0)} bien(s) integre(s) au patrimoine global.",
        })
    if data_profile.get("business_value", 0) > 0:
        events.append({
            "label": "Business",
            "title": "Valeur entrepreneuriale",
            "description": "Une valeur business est maintenant visible dans la carte patrimoniale.",
        })

    return {
        "title": "Histoire de ta richesse",
        "events": events,
    }


def build_opportunity_radar(data_profile: dict):
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    opportunities = [
        {
            "key": "marketing_recurring_offer",
            "title": "Offre recurrente marketing",
            "why_fit": "Compatible avec une expertise existante et une contrainte de temps forte.",
            "time_fit": "Court si l'offre est standardisee.",
            "impact": "Peut augmenter les revenus sans creer un nouveau chantier lourd.",
            "next_action": "Formaliser une offre simple, un prix fixe et une cible precise.",
            "priority": "high",
        },
        {
            "key": "digital_product",
            "title": "Produit numerique issu de l'expertise",
            "why_fit": "Transforme une competence deja presente en actif reutilisable.",
            "time_fit": "Moyen: utile seulement si le format reste tres simple.",
            "impact": "Potentiel de revenu scalable, mais validation commerciale indispensable.",
            "next_action": "Identifier une douleur client repetitive et une promesse vendable.",
            "priority": "medium",
        },
    ]
    if monthly_capacity > 0:
        opportunities.append({
            "key": "automated_investing",
            "title": "Investissement mensuel automatise",
            "why_fit": "La capacite mensuelle existe dans les donnees backend.",
            "time_fit": "Faible charge mentale si la regle est simple.",
            "impact": "Construit une trajectoire patrimoniale sans multiplier les decisions.",
            "next_action": "Fixer un montant prudent et une frequence automatique.",
            "priority": "medium",
        })
    else:
        opportunities.append({
            "key": "small_business_acquisition",
            "title": "Acquisition d'un petit actif digital",
            "why_fit": "Interessant si le business complete les competences existantes.",
            "time_fit": "A filtrer strictement: beaucoup d'opportunites sont incompatibles avec peu de temps.",
            "impact": "Peut creer un levier, mais uniquement avec operations simples.",
            "next_action": "Lister les criteres d'exclusion avant de regarder des deals.",
            "priority": "low",
        })

    return {
        "title": "Radar d'opportunites",
        "principle": "Les opportunites sont filtrees par coherence avec la situation, pas par popularite.",
        "items": opportunities[:3],
    }


def build_decision_engine(data_profile: dict):
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    business_value = float(data_profile.get("business_value") or 0)

    return {
        "title": "Moteur de decisions",
        "decisions": [
            {
                "key": "develop_business",
                "label": "Developper l'activite",
                "cashflow": "+",
                "liquidity": "+",
                "risk": "moyen",
                "freedom_impact": "+++",
                "fit": "fort" if business_value > 0 or monthly_capacity <= 1000 else "moyen",
                "comment": "Levier prioritaire si l'objectif est d'augmenter les revenus avec une competence existante.",
            },
            {
                "key": "buy_real_estate",
                "label": "Acheter un bien immobilier",
                "cashflow": "+/-",
                "liquidity": "-",
                "risk": "moyen",
                "freedom_impact": "++",
                "fit": "moyen" if monthly_capacity > 0 else "faible",
                "comment": "Decision pertinente seulement si la marge mensuelle et la reserve de securite sont suffisantes.",
            },
            {
                "key": "invest_monthly",
                "label": "Investir chaque mois",
                "cashflow": "-",
                "liquidity": "+/-",
                "risk": "modere",
                "freedom_impact": "++",
                "fit": "fort" if monthly_capacity > 0 else "faible",
                "comment": "Decision robuste quand elle reste automatique et proportionnee a la capacite disponible.",
            },
            {
                "key": "balanced_path",
                "label": "Mixer business + investissement",
                "cashflow": "+",
                "liquidity": "+/-",
                "risk": "moyen",
                "freedom_impact": "+++",
                "fit": "fort" if current_wealth > 0 and monthly_capacity > 0 else "moyen",
                "comment": "Chemin coherent si l'utilisateur veut croissance sans dependance a un seul levier.",
            },
        ],
    }


def build_time_value(data_profile: dict):
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    hourly_value = round(monthly_income / 151.67, 2) if monthly_income > 0 else 0

    return {
        "title": "Valeur du temps",
        "hourly_value": hourly_value,
        "monthly_capacity": round(monthly_capacity, 2),
        "basis": "Estimation backend basee sur le revenu mensuel et un temps plein standard.",
        "levers": [
            {"label": "Prestation sur mesure", "time_cost": "eleve", "leverage": "faible a moyen", "reading": "A limiter si le temps familial est rare."},
            {"label": "Offre packagée", "time_cost": "moyen", "leverage": "fort", "reading": "Meilleur rapport temps/revenu si la promesse est claire."},
            {"label": "Produit digital", "time_cost": "initial eleve", "leverage": "fort apres validation", "reading": "Interessant seulement apres preuve de demande."},
        ],
    }


def build_wealth_blocks(data_profile: dict):
    liquid_assets = float(data_profile.get("liquid_assets") or 0)
    security_reserve = float(data_profile.get("security_reserve") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)
    return {
        "title": "Construction par blocs",
        "blocks": [
            {"key": "security", "label": "Bloc securite", "value": liquid_assets, "status": "active" if liquid_assets >= security_reserve and liquid_assets > 0 else "to_build", "description": "Liquidites disponibles et reserve de securite."},
            {"key": "income", "label": "Bloc revenus", "value": float(data_profile.get("monthly_income") or 0), "status": "active" if data_profile.get("monthly_income", 0) else "to_build", "description": "Base de revenus suivie par le backend."},
            {"key": "markets", "label": "Bloc marches financiers", "value": float(data_profile.get("portfolio_value") or 0), "status": "active" if data_profile.get("portfolio_value", 0) else "to_build", "description": "Actifs financiers liquides."},
            {"key": "real_estate", "label": "Bloc immobilier", "value": float(data_profile.get("real_estate_value") or 0), "status": "active" if data_profile.get("real_estate_value", 0) else "to_build", "description": "Actifs immobiliers et valeur estimee."},
            {"key": "business", "label": "Bloc business", "value": float(data_profile.get("business_value") or 0), "status": "active" if data_profile.get("business_value", 0) else "to_build", "description": "Valeur entrepreneuriale, yield assets et ventures."},
            {"key": "passion_assets", "label": "Passion Assets", "value": float(data_profile.get("passion_assets_value") or 0), "status": "active" if data_profile.get("passion_assets_value", 0) else "to_build", "description": "Art, montres, voitures, vins, bijoux et collections declarees."},
            {"key": "debt", "label": "Bloc dette", "value": debt_total, "status": "watch" if debt_total > 0 else "clear", "description": "Dette suivie dans les finances."},
        ],
    }


def build_dependency_detector(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_income = float(data_profile.get("monthly_income") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    signals = []
    if monthly_income > 0 and business_value <= 0:
        signals.append({"type": "income_source", "title": "Dependance au revenu actif", "description": "Le backend voit un revenu mensuel mais pas encore de bloc business valorise.", "severity": "medium"})
    if data_profile.get("portfolio_count", 0) <= 1 and current_wealth > 0:
        signals.append({"type": "asset_concentration", "title": "Dependance a peu d'actifs", "description": "Le patrimoine suivi repose sur peu de lignes mesurables.", "severity": "medium"})
    if not signals:
        signals.append({"type": "balanced", "title": "Aucune dependance majeure detectee", "description": "Les donnees backend ne montrent pas encore de fragilite de dependance dominante.", "severity": "low"})
    return {"title": "Detecteur de dependances", "signals": signals[:3]}


def build_personal_command_center(mission_control: dict, opportunity_radar: dict, dependency_detector: dict, time_value: dict):
    radar_items = opportunity_radar.get("items") or []
    dependencies = dependency_detector.get("signals") or []
    return {
        "title": "Centre de commandement personnel",
        "situation": mission_control.get("decision", {}).get("description"),
        "threat": dependencies[0] if dependencies else None,
        "opportunity": radar_items[0] if radar_items else mission_control.get("opportunity"),
        "mission": mission_control.get("mission"),
        "next_step": radar_items[0].get("next_action") if radar_items else mission_control.get("decision", {}).get("action"),
        "time_value": time_value,
    }


def build_wealth_map(data_profile: dict, wealth_timeline: dict):
    current_wealth = float(data_profile.get("projection_wealth") or data_profile.get("current_wealth") or 0)
    monthly_velocity = float(wealth_timeline.get("monthly_velocity") or 0)
    destination = wealth_timeline.get("next_milestone") or {"label": "1M", "target": 1000000}
    target = float(destination.get("target") or 1000000)
    return {
        "title": "Wealth Map",
        "destination": destination,
        "current_position": round(current_wealth, 2),
        "progress_percent": min(100, round((current_wealth / target) * 100, 1)) if target > 0 else 0,
        "distance_remaining": max(round(target - current_wealth, 2), 0),
        "monthly_velocity": round(monthly_velocity, 2),
        "estimated_label": destination.get("estimated_label"),
        "months_to_destination": destination.get("months_to_target"),
    }


def build_invisible_wealth(data_profile: dict, digital_twin: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    scenarios = digital_twin.get("scenarios") or []
    best = max(scenarios, key=lambda item: float(item.get("value_10y") or 0), default=None)
    projected = float((best or {}).get("value_10y") or current_wealth)
    return {
        "title": "Richesse invisible",
        "current_wealth": round(current_wealth, 2),
        "projected_wealth": round(projected, 2),
        "untapped_capital": max(round(projected - current_wealth, 2), 0),
        "best_path": best,
        "story": "Ecart entre la position actuelle et le meilleur futur simule par le backend.",
    }


def build_family_office_radar(data_profile: dict, weak_signals: dict, dependency_detector: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    liquid_assets = float(data_profile.get("liquid_assets") or 0)
    security_reserve = float(data_profile.get("security_reserve") or 0)
    mobilizable_liquidity = float(data_profile.get("mobilizable_liquidity") or 0)
    portfolio_value = float(data_profile.get("portfolio_value") or 0)
    real_estate_value = float(data_profile.get("real_estate_value") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    debt_total = float(data_profile.get("debt_total") or 0)
    concentration_flag = any(
        item.get("type") in {"concentration", "asset_concentration"}
        for item in (weak_signals.get("signals") or []) + (dependency_detector.get("signals") or [])
    )

    def status(score: int):
        if score >= 75:
            return "green"
        if score >= 45:
            return "amber"
        return "red"

    passion_assets_value = float(data_profile.get("passion_assets_value") or 0)
    diversification_domains = sum(1 for value in [portfolio_value, real_estate_value, business_value, passion_assets_value] if value > 0)
    liquidity_score = 40
    if liquid_assets > 0:
        liquidity_score = 75 if liquid_assets >= security_reserve else 55
    if mobilizable_liquidity > 0:
        liquidity_score = min(100, liquidity_score + 10)
    items = [
        ("growth", "Croissance", 80 if monthly_capacity > 0 or business_value > 0 else 40),
        ("diversification", "Diversification", 35 + diversification_domains * 20),
        ("concentration", "Concentration", 35 if concentration_flag else 80),
        ("income", "Revenus", 80 if data_profile.get("monthly_income", 0) else 35),
        ("liquidity", "Liquidite", liquidity_score),
        ("debt", "Dette", 40 if debt_total > max(current_wealth * 0.35, 1) else 75),
    ]
    return {
        "title": "Family Office Radar",
        "items": [
            {"key": key, "label": label, "score": min(100, score), "status": status(min(100, score))}
            for key, label, score in items
        ],
    }


def build_hidden_wealth(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    completion = float(data_profile.get("completion_percent") or 0)
    items = []
    if monthly_income > 0:
        expertise_months = 12 if completion >= 60 else 6
        network_months = 4 if completion >= 60 else 3
        items.append({"key": "expertise", "label": "Expertise professionnelle", "potential_value": round(max(monthly_income * expertise_months, 15000), 2), "confidence": "contextual", "description": "Potentiel prudent de monetisation d'une competence deja presente, a valider par une offre concrete."})
        items.append({"key": "network", "label": "Reseau professionnel", "potential_value": round(max(monthly_income * network_months, 10000), 2), "confidence": "light", "description": "Potentiel commercial indicatif lie aux contacts accessibles, non acquis tant qu'aucune opportunite n'est signee."})
    if business_value > 0:
        business_multiplier = 1.25 if business_value >= 10000 else 1
        items.append({"key": "business", "label": "Business existant", "potential_value": round(business_value * business_multiplier, 2), "confidence": "asset_based" if business_value >= 10000 else "early_signal", "description": "Potentiel base sur le business deja suivi; a structurer avant d'etre considere comme une valorisation."})
    if monthly_capacity > 0:
        items.append({"key": "borrowing_capacity", "label": "Capacite d'emprunt theorique", "potential_value": round(monthly_capacity * 240, 2), "confidence": "simulation", "description": "Simulation prudente basee sur la capacite mensuelle, sans validation bancaire."})
    activable = sum(float(item.get("potential_value") or 0) for item in items)
    return {"title": "Patrimoine cache", "visible_wealth": round(current_wealth, 2), "activable_wealth": round(activable, 2), "total_potential": round(current_wealth + activable, 2), "items": items, "basis": "Estimation backend de valeur activable, non comptabilisee comme patrimoine acquis."}


def build_gravity_center(data_profile: dict, hidden_wealth: dict):
    visible_domains = [("investments", "Financier", float(data_profile.get("portfolio_value") or 0)), ("real_estate", "Immobilier", float(data_profile.get("real_estate_value") or 0)), ("business", "Business", float(data_profile.get("business_value") or 0)), ("passion_assets", "Passion Assets", float(data_profile.get("passion_assets_value") or 0))]
    visible_total = sum(value for _, _, value in visible_domains)
    future_domains = visible_domains + [("hidden", "Patrimoine activable", float(hidden_wealth.get("activable_wealth") or 0))]
    future_total = sum(value for _, _, value in future_domains)
    dominant_visible = max(visible_domains, key=lambda item: item[2], default=("none", "Aucun", 0))
    dominant_future = max(future_domains, key=lambda item: item[2], default=("none", "Aucun", 0))
    return {
        "title": "Centre de gravite",
        "visible": [{"key": key, "label": label, "value": round(value, 2), "weight": round((value / visible_total) * 100, 1) if visible_total > 0 else 0} for key, label, value in visible_domains],
        "future": [{"key": key, "label": label, "value": round(value, 2), "weight": round((value / future_total) * 100, 1) if future_total > 0 else 0} for key, label, value in future_domains],
        "dominant_visible": dominant_visible[1],
        "dominant_future": dominant_future[1],
        "reading": f"Le patrimoine visible depend surtout de {dominant_visible[1].lower()}, mais le potentiel futur peut basculer vers {dominant_future[1].lower()}." if future_total > 0 else "Le centre de gravite sera lisible quand davantage de donnees seront renseignees.",
        "hidden_count": len(hidden_wealth.get("items") or []),
    }


def build_stress_tests(data_profile: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    real_estate_value = float(data_profile.get("real_estate_value") or 0)
    business_value = float(data_profile.get("business_value") or 0)
    portfolio_value = float(data_profile.get("portfolio_value") or 0)
    passion_assets_value = float(data_profile.get("passion_assets_value") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    return {"title": "Stress tests Family Office", "base_value": round(current_wealth, 2), "tests": [
        {"key": "real_estate_down_20", "label": "Immobilier -20%", "result_value": round(current_wealth - real_estate_value * 0.2, 2), "delta": round(-real_estate_value * 0.2, 2), "reading": "Mesure la sensibilite a une baisse immobiliere."},
        {"key": "markets_down_15", "label": "Marches financiers -15%", "result_value": round(current_wealth - portfolio_value * 0.15, 2), "delta": round(-portfolio_value * 0.15, 2), "reading": "Mesure la sensibilite aux actifs financiers liquides."},
        {"key": "passion_assets_down_25", "label": "Passion Assets -25%", "result_value": round(current_wealth - passion_assets_value * 0.25, 2), "delta": round(-passion_assets_value * 0.25, 2), "reading": "Mesure la sensibilite aux valeurs declarees non liquides."},
        {"key": "business_double", "label": "Business x2", "result_value": round(current_wealth + business_value, 2), "delta": round(business_value, 2), "reading": "Mesure l'effet d'une acceleration business."},
        {"key": "extra_500_month", "label": "+500 EUR/mois sur 10 ans", "result_value": round(current_wealth + (monthly_capacity + 500) * 12 * 10, 2), "delta": round(500 * 12 * 10, 2), "reading": "Mesure la puissance d'un effort mensuel additionnel avant rendement."},
    ]}


def build_leverage_engine(data_profile: dict, hidden_wealth: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    deployable_liquidity = float(data_profile.get("deployable_liquidity") or 0)
    hidden_value = float(hidden_wealth.get("activable_wealth") or 0)
    has_investment_base = monthly_capacity > 0 or deployable_liquidity > 0
    levers = [
        {"key": "business", "label": "Developper le business", "impact_score": min(100, 45 + int(hidden_value / max(current_wealth or 1, 1) * 35)), "reason": "Fort si une expertise ou une valeur activable existe."},
        {"key": "real_estate", "label": "Immobilier", "impact_score": 70 if has_investment_base else 45, "reason": "Pertinent si une marge mensuelle ou une liquidite mobilisable peut soutenir le levier."},
        {"key": "markets", "label": "Marches financiers", "impact_score": 60 if has_investment_base else 40, "reason": "Robuste si l'investissement reste automatique, progressif et diversifie."},
        {"key": "crypto", "label": "Crypto / actifs risques", "impact_score": 35, "reason": "Levier secondaire tant que la base patrimoniale n'est pas stabilisee."},
    ]
    levers = sorted(levers, key=lambda item: item["impact_score"], reverse=True)
    return {"title": "Moteur de leviers", "main_lever": levers[0] if levers else None, "levers": levers, "hidden_assets_count": len(hidden_wealth.get("items") or [])}


def build_life_wealth(data_profile: dict):
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    monthly_expenses = float(data_profile.get("monthly_expenses") or 0)
    liquid_assets = float(data_profile.get("liquid_assets") or 0)
    mobilizable_liquidity = float(data_profile.get("mobilizable_liquidity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    domains = sum(1 for value in [data_profile.get("portfolio_value", 0), data_profile.get("real_estate_value", 0), data_profile.get("business_value", 0), data_profile.get("passion_assets_value", 0)] if float(value or 0) > 0)
    reserve_months = liquid_assets / monthly_expenses if monthly_expenses > 0 else 0
    security = 35
    if monthly_expenses > 0:
        security = min(100, round((reserve_months / 12) * 80))
        if monthly_capacity > 0:
            security = min(100, security + 10)
        if mobilizable_liquidity > 0:
            security = min(100, security + 10)
    elif liquid_assets > 0:
        security = 75
    return {"title": "Patrimoine de vie", "dimensions": [
        {"key": "security", "label": "Securite", "score": security},
        {"key": "freedom", "label": "Liberte", "score": min(100, round((current_wealth / 1000000) * 100, 1))},
        {"key": "transmission", "label": "Transmission", "score": 20},
        {"key": "diversification", "label": "Diversification", "score": min(100, 25 + domains * 20)},
        {"key": "growth", "label": "Croissance", "score": 70 if monthly_capacity > 0 or data_profile.get("business_value", 0) else 40},
    ]}


def build_future_film(data_profile: dict, digital_twin: dict, leverage_engine: dict):
    current_year = date.today().year
    current_wealth = float(data_profile.get("current_wealth") or 0)
    best = (digital_twin.get("scenarios") or [{}])[0]
    main_lever = leverage_engine.get("main_lever") or {}
    value_5y = float(best.get("value_5y") or current_wealth)
    value_10y = float(best.get("value_10y") or value_5y)
    return {"title": "Film du futur patrimonial", "chapters": [
        {"year": current_year, "title": "La base devient visible", "wealth": round(current_wealth, 2), "narrative": "White Rock transforme la photo actuelle en point de depart mesurable."},
        {"year": current_year + 2, "title": "Le levier prioritaire s'active", "wealth": round((current_wealth + value_5y) / 2, 2), "narrative": f"Le levier {str(main_lever.get('label') or 'principal').lower()} commence a peser dans la trajectoire."},
        {"year": current_year + 5, "title": "La trajectoire change d'echelle", "wealth": round(value_5y, 2), "narrative": "Les efforts recurrents et les actifs suivis commencent a creer une trajectoire composee."},
        {"year": current_year + 10, "title": "Le futur alternatif devient tangible", "wealth": round(value_10y, 2), "narrative": "Le patrimoine projete n'est plus seulement une valeur: c'est une architecture de vie."},
    ]}


def build_family_office_scorecard(data_profile: dict, life_wealth: dict):
    dimensions = {item.get("key"): item.get("score") for item in life_wealth.get("dimensions") or []}
    return {"title": "Family Office Scorecard", "dimensions": [
        {"key": "capital", "label": "Capital", "score": min(100, round((float(data_profile.get("current_wealth") or 0) / 1000000) * 100, 1))},
        {"key": "income", "label": "Revenus", "score": min(100, round((float(data_profile.get("monthly_income") or 0) / 10000) * 100, 1))},
        {"key": "resilience", "label": "Resilience", "score": dimensions.get("security", 0)},
        {"key": "diversification", "label": "Diversification", "score": dimensions.get("diversification", 0)},
        {"key": "growth", "label": "Croissance", "score": dimensions.get("growth", 0)},
        {"key": "transmission", "label": "Transmission", "score": dimensions.get("transmission", 0)},
    ]}


def build_board_briefing(personal_command_center: dict, gravity_center: dict, stress_tests: dict):
    tests = stress_tests.get("tests") or []
    downside = min(tests, key=lambda item: float(item.get("delta") or 0), default=None)
    return {"title": "Conseil d'administration personnel", "headline": personal_command_center.get("situation"), "what_changed": gravity_center.get("reading"), "main_risk": (personal_command_center.get("threat") or {}).get("title"), "main_opportunity": (personal_command_center.get("opportunity") or {}).get("title"), "stress_watch": downside, "next_step": personal_command_center.get("next_step")}


def build_memorable_wealth_insight(data_profile: dict, hidden_wealth: dict, gravity_center: dict, wealth_map: dict, leverage_engine: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    activable = float(hidden_wealth.get("activable_wealth") or 0)
    total_potential = float(hidden_wealth.get("total_potential") or 0)
    dominant_future = gravity_center.get("dominant_future")
    main_lever = leverage_engine.get("main_lever") or {}
    destination = wealth_map.get("destination") or {}
    estimated_label = wealth_map.get("estimated_label") or destination.get("estimated_label")
    if current_wealth > 0 and activable >= current_wealth * 2:
        return f"Ton patrimoine activable represente environ {round(activable / current_wealth, 1)} fois ton patrimoine visible: c'est probablement le signal le plus important a surveiller."
    if dominant_future and main_lever.get("label"):
        return f"Ton futur patrimonial semble moins dependre de ce que tu possedes deja que de ta capacite a activer {str(main_lever.get('label')).lower()}."
    if estimated_label:
        return f"A ce rythme, ton prochain palier patrimonial devient lisible autour de {estimated_label}."
    if total_potential > current_wealth:
        return "White Rock detecte deja plus de potentiel activable que de capital visible."
    return "Le premier enjeu est de rendre la trajectoire assez claire pour que chaque action compte."


def build_family_office_ceo_dashboard(data_profile: dict, strategic_intelligence: dict, wealth_narrative: dict, family_office_intelligence: dict, missions: list[dict]):
    monthly_income = float(data_profile.get("monthly_income") or 0)
    monthly_expenses = float(data_profile.get("monthly_expenses") or 0)
    monthly_capacity = float(data_profile.get("monthly_capacity") or 0)
    current_wealth = float(data_profile.get("current_wealth") or 0)
    burn_rate = monthly_expenses
    runway_months = None
    if burn_rate > 0 and monthly_capacity < 0:
        runway_months = max(0, round(current_wealth / burn_rate, 1))
    elif monthly_capacity >= 0:
        runway_months = "stable"
    cards = strategic_intelligence.get("cards") or []
    decision = next((card for card in cards if card.get("key") == "decision"), {})
    risk = next((card for card in cards if card.get("key") == "risk"), {})
    scorecard = family_office_intelligence.get("scorecard") or []
    weakest_dimension = min(scorecard, key=lambda item: float(item.get("score") or 0), default=None)
    operating_reading = "Ton systeme produit une capacite mensuelle positive." if monthly_capacity > 0 else "Ton systeme genere du revenu, mais la marge de manoeuvre reste fragile." if monthly_income > 0 else "Le cockpit doit encore consolider les revenus pour lire la marge reelle."
    return {"title": "Family Office CEO", "question": "Comment piloter ma vie financiere comme une holding personnelle ?", "operating_reading": operating_reading, "wealth": round(current_wealth, 2), "monthly_income": round(monthly_income, 2), "monthly_expenses": round(monthly_expenses, 2), "monthly_capacity": round(monthly_capacity, 2), "burn_rate": round(burn_rate, 2), "runway_months": runway_months, "debt_total": round(float(data_profile.get("debt_total") or 0), 2), "active_projects": int(data_profile.get("completed_steps") or 0), "objective": wealth_narrative.get("memorable_insight"), "decision": decision, "risk": risk, "weakest_dimension": weakest_dimension, "mission": missions[0] if missions else None}


def build_wealth_intelligence(wealth_narrative: dict, family_office_view: dict, hidden_wealth: dict, gravity_center: dict):
    return {"title": "Wealth Intelligence", "question": "Ou j'en suis ?", "headline": wealth_narrative.get("headline"), "narrative": wealth_narrative.get("narrative"), "memorable_insight": wealth_narrative.get("memorable_insight"), "why_it_matters": wealth_narrative.get("why_it_matters"), "visible_wealth": wealth_narrative.get("visible_wealth"), "activable_wealth": wealth_narrative.get("activable_wealth"), "total_potential": wealth_narrative.get("total_potential"), "gravity_reading": gravity_center.get("reading") or wealth_narrative.get("gravity_reading"), "domains": family_office_view.get("allocation") or [], "hidden_items": hidden_wealth.get("items") or []}


def build_decision_intelligence(strategic_intelligence: dict, family_office_ceo: dict):
    cards = strategic_intelligence.get("cards") or []
    decision = next((card for card in cards if card.get("key") == "decision"), {})
    risk = next((card for card in cards if card.get("key") == "risk"), {})
    opportunity = next((card for card in cards if card.get("key") == "opportunity"), {})
    leverage = next((card for card in cards if card.get("key") == "leverage"), {})
    mission = family_office_ceo.get("mission") or {}
    return {"title": "Decision Intelligence", "question": "Qu'est-ce que je fais maintenant ?", "why_it_matters": "Une bonne interface patrimoniale ne montre pas toutes les possibilites: elle isole la decision utile.", "decision": decision, "risk": risk, "opportunity": opportunity, "leverage": leverage, "next_action": decision.get("action") or opportunity.get("action") or mission.get("description"), "cards": [risk, opportunity, decision, leverage]}


def build_wealth_narrative(data_profile: dict, hidden_wealth: dict, gravity_center: dict, wealth_map: dict, leverage_engine: dict):
    current_wealth = float(data_profile.get("current_wealth") or 0)
    activable = float(hidden_wealth.get("activable_wealth") or 0)
    destination = wealth_map.get("destination") or {}
    main_lever = leverage_engine.get("main_lever") or {}
    estimated_label = wealth_map.get("estimated_label") or destination.get("estimated_label")
    memorable_insight = build_memorable_wealth_insight(data_profile, hidden_wealth, gravity_center, wealth_map, leverage_engine)
    if activable > current_wealth and main_lever.get("label"):
        narrative = f"Ton patrimoine visible repose aujourd'hui sur une base mesurable. Mais la lecture Family Office montre autre chose: ton potentiel futur peut se deplacer vers {str(gravity_center.get('dominant_future') or 'un levier futur').lower()}, avec {str(main_lever.get('label')).lower()} comme accelerateur principal. Ce n'est pas seulement une question de valeur detenue: c'est une question de capital encore activable."
    elif estimated_label:
        narrative = f"Ta trajectoire est maintenant lisible: le prochain palier patrimonial est estime autour de {estimated_label}. White Rock rend la distance, le rythme et la decision suivante visibles."
    else:
        narrative = "White Rock commence a transformer les donnees patrimoniales en trajectoire. Plus les revenus, actifs et objectifs seront renseignes, plus le recit deviendra precis."
    return {"title": "Wealth Narrative", "headline": "Ce que raconte ta trajectoire", "narrative": narrative, "memorable_insight": memorable_insight, "why_it_matters": "Parce que les decisions patrimoniales deviennent plus simples quand la trajectoire raconte une histoire claire.", "visible_wealth": round(current_wealth, 2), "activable_wealth": round(activable, 2), "total_potential": hidden_wealth.get("total_potential"), "next_milestone": destination, "main_lever": main_lever, "gravity_reading": gravity_center.get("reading")}


def build_future_intelligence(wealth_map: dict, wealth_timeline: dict, digital_twin: dict, wealth_gps: dict, future_film: dict):
    destination = wealth_map.get("destination") or {}
    months_to_target = wealth_map.get("months_to_destination") or destination.get("months_to_target")
    time_to_next = f"{int(months_to_target)} mois" if months_to_target else None
    why_it_matters = f"Le prochain palier n'est plus abstrait: il peut etre suivi comme une distance temporelle de {time_to_next}." if time_to_next else "Cette vue transforme le patrimoine en trajectoire, puis la trajectoire en decisions."
    return {"title": "Future Intelligence", "question": "Ou vais-je ?", "why_it_matters": why_it_matters, "time_to_next": time_to_next, "position": {"current": wealth_map.get("current_position"), "destination": wealth_map.get("destination"), "progress_percent": wealth_map.get("progress_percent"), "distance_remaining": wealth_map.get("distance_remaining"), "monthly_velocity": wealth_map.get("monthly_velocity"), "estimated_label": wealth_map.get("estimated_label")}, "timeline": wealth_timeline.get("stages") or [], "routes": wealth_gps.get("routes") or [], "simulations": digital_twin.get("scenarios") or [], "film": future_film.get("chapters") or []}


def build_strategic_intelligence(mission_control: dict, opportunity_radar: dict, decision_engine: dict, leverage_engine: dict, board_briefing: dict):
    first_opportunity = (opportunity_radar.get("items") or [{}])[0]
    main_lever = leverage_engine.get("main_lever") or {}
    return {"title": "Strategic Intelligence", "question": "Que dois-je faire ?", "cards": [
        {"key": "risk", "label": "Risque principal", "title": (mission_control.get("risk") or {}).get("title"), "description": (mission_control.get("risk") or {}).get("description")},
        {"key": "opportunity", "label": "Opportunite principale", "title": first_opportunity.get("title"), "description": first_opportunity.get("impact"), "action": first_opportunity.get("next_action")},
        {"key": "decision", "label": "Decision du moment", "title": (mission_control.get("decision") or {}).get("title"), "description": (mission_control.get("decision") or {}).get("description"), "action": board_briefing.get("next_step")},
        {"key": "leverage", "label": "Levier principal", "title": main_lever.get("label"), "description": main_lever.get("reason"), "score": main_lever.get("impact_score")},
    ], "decision_matrix": decision_engine.get("decisions") or []}


def build_family_office_intelligence(family_office_scorecard: dict, stress_tests: dict, dependency_detector: dict, weak_signals: dict, life_wealth: dict, family_office_radar: dict):
    return {"title": "Family Office Intelligence", "question": "Quelle est la solidite globale ?", "scorecard": family_office_scorecard.get("dimensions") or [], "stress_tests": stress_tests.get("tests") or [], "dependencies": dependency_detector.get("signals") or [], "weak_signals": weak_signals.get("signals") or [], "life_dimensions": life_wealth.get("dimensions") or [], "radar": family_office_radar.get("items") or []}


def apply_plan_experience_gates(
    plan: str,
    wealth_intelligence: dict,
    future_intelligence: dict,
    strategic_intelligence: dict,
    decision_intelligence: dict,
    family_office_intelligence: dict,
    family_office_ceo: dict,
):
    normalized = normalize_plan(plan)

    if not plan_allows(normalized, "GOLD"):
        future_intelligence = {
            **future_intelligence,
            "routes": [],
            "simulations": [],
            "film": (future_intelligence.get("film") or [])[:2],
        }
        return {
            "wealth_intelligence": wealth_intelligence,
            "future_intelligence": future_intelligence,
            "strategic_intelligence": None,
            "decision_intelligence": None,
            "family_office_intelligence": None,
            "family_office_ceo": None,
        }

    if not plan_allows(normalized, "ELITE"):
        wealth_intelligence = {
            **wealth_intelligence,
            "hidden_items": (wealth_intelligence.get("hidden_items") or [])[:2],
        }
        future_intelligence = {
            **future_intelligence,
            "simulations": (future_intelligence.get("simulations") or [])[:1],
            "routes": (future_intelligence.get("routes") or [])[:1],
        }
        family_office_intelligence = {
            **family_office_intelligence,
            "stress_tests": (family_office_intelligence.get("stress_tests") or [])[:2],
            "dependencies": (family_office_intelligence.get("dependencies") or [])[:2],
            "weak_signals": [],
            "life_dimensions": [],
            "radar": [],
        }
        family_office_ceo = None

    if not plan_allows(normalized, "LIBERTY"):
        strategic_intelligence = {
            **strategic_intelligence,
            "decision_matrix": [],
            "advanced_arbitrages": [],
            "family_office_board": None,
        }
        decision_intelligence = {
            **decision_intelligence,
            "decision_matrix": [],
            "advanced_arbitrages": [],
            "family_office_board": None,
        }

    if not plan_allows(normalized, "LEGACY") and family_office_intelligence:
        family_office_intelligence = {
            **family_office_intelligence,
            "dynasty_layer": None,
        }

    return {
        "wealth_intelligence": wealth_intelligence,
        "future_intelligence": future_intelligence,
        "strategic_intelligence": strategic_intelligence,
        "decision_intelligence": decision_intelligence,
        "family_office_intelligence": family_office_intelligence,
        "family_office_ceo": family_office_ceo,
    }


@router.get("/context")
def product_context(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        plan_row = conn.execute(text("""
            SELECT
                users.plan AS user_plan,
                users.is_founder,
                users.founder_tier,
                users.founder_discount,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.id = :user_id
        """), {"user_id": user_id}).fetchone()

        plan = resolve_effective_plan(
            plan_row.user_plan if plan_row else "FREE",
            plan_row.subscription_plan if plan_row else None,
            plan_row.subscription_status if plan_row else None,
        )
        score = get_score(email)
        entitlements = build_entitlements(plan)
        data_profile = build_data_profile(conn, user_id)
        progression = build_progression(conn, user_id, score, plan)
        modules = build_modules(plan, score)
        academy_progress = get_academy_progress(conn, user_id)
        mission_progress = get_mission_progress(conn, user_id)
        missions = build_missions(data_profile, score, plan, academy_progress, mission_progress)
        wealth_academy = build_wealth_academy(data_profile, missions, score, plan, academy_progress)
        strategic_brief = build_strategic_brief(data_profile, score, plan)
        future_view = build_future_view(data_profile, score, plan)
        wealth_timeline = build_wealth_timeline(data_profile, future_view)
        mission_control = build_mission_control(strategic_brief, missions, future_view)
        family_office_view = build_family_office_view(data_profile, plan)
        wealth_gps = build_wealth_gps(data_profile, future_view)
        digital_twin = build_digital_twin(data_profile)
        weak_signals = build_weak_signals(data_profile)
        self_benchmark = build_self_benchmark(conn, user_id, data_profile)
        wealth_story = build_wealth_story(data_profile, progression)
        opportunity_radar = build_opportunity_radar(data_profile)
        decision_engine = build_decision_engine(data_profile)
        time_value = build_time_value(data_profile)
        wealth_blocks = build_wealth_blocks(data_profile)
        dependency_detector = build_dependency_detector(data_profile)
        personal_command_center = build_personal_command_center(
            mission_control,
            opportunity_radar,
            dependency_detector,
            time_value,
        )
        wealth_map = build_wealth_map(data_profile, wealth_timeline)
        invisible_wealth = build_invisible_wealth(data_profile, digital_twin)
        family_office_radar = build_family_office_radar(data_profile, weak_signals, dependency_detector)
        hidden_wealth = build_hidden_wealth(data_profile)
        gravity_center = build_gravity_center(data_profile, hidden_wealth)
        stress_tests = build_stress_tests(data_profile)
        leverage_engine = build_leverage_engine(data_profile, hidden_wealth)
        life_wealth = build_life_wealth(data_profile)
        future_film = build_future_film(data_profile, digital_twin, leverage_engine)
        family_office_scorecard = build_family_office_scorecard(data_profile, life_wealth)
        board_briefing = build_board_briefing(personal_command_center, gravity_center, stress_tests)
        wealth_narrative = build_wealth_narrative(data_profile, hidden_wealth, gravity_center, wealth_map, leverage_engine)
        future_intelligence = build_future_intelligence(wealth_map, wealth_timeline, digital_twin, wealth_gps, future_film)
        strategic_intelligence = build_strategic_intelligence(mission_control, opportunity_radar, decision_engine, leverage_engine, board_briefing)
        family_office_intelligence = build_family_office_intelligence(family_office_scorecard, stress_tests, dependency_detector, weak_signals, life_wealth, family_office_radar)
        family_office_ceo = build_family_office_ceo_dashboard(data_profile, strategic_intelligence, wealth_narrative, family_office_intelligence, missions)
        profile_row = conn.execute(text("""
            SELECT first_name
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()
        daily_loop = get_daily_briefing_loop(conn, user_id)
        ceo_daily_briefing = build_ceo_daily_briefing(
            data_profile,
            score,
            plan,
            missions,
            mission_control,
            future_view,
            opportunity_radar,
            board_briefing,
            profile_row.first_name if profile_row else None,
            wealth_academy,
            daily_loop,
        )
        ceo_daily_briefing = attach_daily_briefing_loop(
            ceo_daily_briefing,
            daily_loop,
        )
        wealth_intelligence = build_wealth_intelligence(wealth_narrative, family_office_view, hidden_wealth, gravity_center)
        decision_intelligence = build_decision_intelligence(strategic_intelligence, family_office_ceo)
        gated_experience = apply_plan_experience_gates(
            plan,
            wealth_intelligence,
            future_intelligence,
            strategic_intelligence,
            decision_intelligence,
            family_office_intelligence,
            family_office_ceo,
        )
        wealth_intelligence = gated_experience["wealth_intelligence"]
        future_intelligence = gated_experience["future_intelligence"]
        strategic_intelligence = gated_experience["strategic_intelligence"]
        decision_intelligence = gated_experience["decision_intelligence"]
        family_office_intelligence = gated_experience["family_office_intelligence"]
        family_office_ceo = gated_experience["family_office_ceo"]

    return {
        "plan": plan,
        "next_plan": get_next_plan(plan),
        "score": score,
        "entitlements": entitlements,
        "progression": progression,
        "data_profile": data_profile,
        "modules": modules,
        "missions": missions,
        "wealth_academy": wealth_academy,
        "strategic_brief": strategic_brief,
        "mission_control": mission_control,
        "future_view": future_view,
        "wealth_timeline": wealth_timeline,
        "family_office_view": family_office_view,
        "wealth_gps": wealth_gps,
        "digital_twin": digital_twin,
        "weak_signals": weak_signals,
        "self_benchmark": self_benchmark,
        "wealth_story": wealth_story,
        "opportunity_radar": opportunity_radar,
        "decision_engine": decision_engine,
        "time_value": time_value,
        "wealth_blocks": wealth_blocks,
        "dependency_detector": dependency_detector,
        "personal_command_center": personal_command_center,
        "wealth_map": wealth_map,
        "invisible_wealth": invisible_wealth,
        "family_office_radar": family_office_radar,
        "hidden_wealth": hidden_wealth,
        "gravity_center": gravity_center,
        "stress_tests": stress_tests,
        "leverage_engine": leverage_engine,
        "life_wealth": life_wealth,
        "future_film": future_film,
        "family_office_scorecard": family_office_scorecard,
        "board_briefing": board_briefing,
        "wealth_narrative": wealth_narrative,
        "wealth_intelligence": wealth_intelligence,
        "future_intelligence": future_intelligence,
        "strategic_intelligence": strategic_intelligence,
        "decision_intelligence": decision_intelligence,
        "family_office_intelligence": family_office_intelligence,
        "family_office_ceo": family_office_ceo,
        "ceo_daily_briefing": ceo_daily_briefing,
        "founder": {
            "is_founder": bool(plan_row.is_founder) if plan_row else False,
            "tier": plan_row.founder_tier if plan_row else None,
            "discount": int(plan_row.founder_discount or 0) if plan_row else 0,
        },
    }
