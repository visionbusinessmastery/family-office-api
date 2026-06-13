# =========================
# GAMIFICATION API DASHBOARD
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user
import json
import hashlib
from datetime import datetime

from core.cache import redis_client
from intelligence.gamification.progress_service import ensure_gamification_tables
from product.entitlements import plan_allows, resolve_effective_plan
from product.routes import ensure_product_tables

router = APIRouter()
GAMIFICATION_STATE_VERSION = "gamification-v1"
XP_TO_NEXT_LEVEL = 1000


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


def stamp_state(payload: dict) -> dict:
    xp = int(payload.get("xp") or 0)
    payload = {
        **payload,
        "xp_to_next_level": payload.get("xp_to_next_level", XP_TO_NEXT_LEVEL),
        "progress_xp": payload.get("progress_xp", xp % XP_TO_NEXT_LEVEL),
        "progress_percent": payload.get(
            "progress_percent",
            min(100, ((xp % XP_TO_NEXT_LEVEL) / XP_TO_NEXT_LEVEL) * 100),
        ),
    }
    stamped = {
        **payload,
        "version": GAMIFICATION_STATE_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }
    stamped.pop("data_hash", None)
    stamped["data_hash"] = hashlib.sha256(
        json.dumps(stamped, sort_keys=True, default=str).encode()
    ).hexdigest()
    return stamped


def build_affiliations(conn, user_id: int):
    suggestions = []

    finance = conn.execute(
        text("""
            SELECT type, COALESCE(SUM(amount), 0) AS total
            FROM finance_items
            WHERE user_id = :user_id
            GROUP BY type
        """),
        {"user_id": user_id}
    ).fetchall()

    totals = {row.type: float(row.total or 0) for row in finance}

    if totals.get("epargne", 0) < max(totals.get("charges", 0), 1):
        suggestions.append({
            "title": "Compte epargne ou cash management",
            "reason": "Renforcer le matelas de securite avant de prendre plus de risque.",
            "priority": "high",
        })

    if totals.get("dettes", 0) > totals.get("epargne", 0):
        suggestions.append({
            "title": "Courtier credit / restructuration",
            "reason": "Optimiser le cout de la dette peut liberer du cashflow.",
            "priority": "medium",
        })

    suggestions.append({
        "title": "Plateforme d'investissement adaptee au profil",
        "reason": "Comparer les frais, la liquidite et les supports avant allocation.",
        "priority": "medium",
    })

    return suggestions[:3]


def build_gamification_actions(score: float, level):
    actions = []

    if score >= 70:
        actions.append({
            "title": "Mission Advanced",
            "description": "Choisir une opportunite prioritaire et definir une action executable en 7 jours.",
            "xp": 150,
        })
        actions.append({
            "title": "Optimisation portefeuille",
            "description": "Verifier la plus forte exposition et reduire le risque si elle depasse ton seuil.",
            "xp": 120,
        })
    else:
        actions.append({
            "title": "Base financiere",
            "description": "Completer revenus, charges, dettes et epargne pour debloquer plus de signaux.",
            "xp": 100,
        })

    return actions


def build_upgrade(score: float, level, plan: str = "FREE"):
    level_text = str(level or "").upper()

    if plan_allows(plan, "LEGACY") or level_text in ["LEGACY", "DYNASTY ARCHITECT"]:
        return {
            "recommended_plan": "legacy",
            "title": "Legacy - Dynasty Office",
            "description": "Construire est difficile. Preserver l'est encore plus.",
        }

    if plan_allows(plan, "LIBERTY"):
        return {
            "recommended_plan": "legacy",
            "title": "Legacy - Dynasty Office",
            "description": "Le prochain seuil concerne la transmission, la gouvernance et la protection familiale.",
        }

    if level_text in ["LIBERTY"] or score >= 85:
        return {
            "recommended_plan": "liberty",
            "title": "Liberty - Financial Freedom",
            "description": "Le vrai luxe est la stabilite. Ethan peut t'aider a structurer une liberte plus durable.",
        }

    if score >= 70 or level_text in ["ADVANCED", "ELITE"]:
        return {
            "recommended_plan": "elite",
            "title": "Passer au plan Elite - Wealth OS",
            "description": "Ton niveau justifie multi-user, gouvernance, guidance premium et consolidation patrimoniale.",
        }

    return {
        "recommended_plan": "gold",
        "title": "Debloquer Gold - Growth",
        "description": "Acceder au portefeuille avance, immobilier, analytics, opportunites et recommandations Ethan.",
    }


def parse_metadata(value):
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except Exception:
        return {}


def timeline_title(event_type: str, metadata: dict | None = None):
    metadata = metadata or {}
    explicit_title = metadata.get("title") or metadata.get("mission_title")
    if explicit_title:
        return explicit_title

    event_type = str(event_type or "").lower()
    if "mission" in event_type:
        return "Mission patrimoniale validee"
    if "badge" in event_type:
        return "Accomplissement debloque"
    if "profile" in event_type:
        return "Profil enrichi"
    if "portfolio" in event_type or "asset" in event_type:
        return "Patrimoine mis a jour"
    if "finance" in event_type or "cashflow" in event_type:
        return "Contexte financier enrichi"
    return "Progression enregistree"


def timeline_description(event_type: str, metadata: dict | None = None):
    metadata = metadata or {}
    explicit_description = metadata.get("description") or metadata.get("reason")
    if explicit_description:
        return explicit_description

    event_type = str(event_type or "").lower()
    if "mission" in event_type:
        return "Une action mesurable a ete ajoutee a ton parcours White Rock."
    if "badge" in event_type:
        return "Un jalon de progression a ete atteint."
    if "profile" in event_type:
        return "Ton profil devient plus exploitable pour le pilotage patrimonial."
    if "portfolio" in event_type or "asset" in event_type:
        return "Une nouvelle information patrimoniale ameliore la vision consolidee."
    if "finance" in event_type or "cashflow" in event_type:
        return "Le contexte revenus, charges ou epargne devient plus lisible."
    return "Un evenement de progression a ete enregistre par White Rock."


def _action_label(action_key: str | None):
    return {
        "decide": "Decision prise",
        "ignore": "Action ignoree",
        "automate": "Automatisation demandee",
    }.get(action_key or "", "Action quotidienne")


def _status_label(status: str | None):
    return {
        "decided": "Decision prise",
        "ignored": "Ignore",
        "automation_requested": "Automatisation demandee",
        "completed": "Valide",
        "done": "Termine",
        "todo": "A faire",
        "in_progress": "En cours",
        "cancelled": "Annule",
    }.get(status or "", "Enregistre")


def build_progression_timeline(conn, user_id: int):
    ensure_gamification_tables(conn)
    ensure_product_tables(conn)

    events = []

    xp_rows = conn.execute(text("""
        SELECT event_type, xp, metadata, created_at
        FROM xp_events
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 25
    """), {"user_id": user_id}).fetchall()

    for row in xp_rows:
        metadata = parse_metadata(row.metadata)
        events.append({
            "date": row.created_at.isoformat() if row.created_at else None,
            "type": row.event_type or "xp_event",
            "title": timeline_title(row.event_type, metadata),
            "description": timeline_description(row.event_type, metadata),
            "impact": metadata.get("impact") or "Ameliore la qualite du pilotage patrimonial.",
            "xp": int(row.xp or 0),
            "source": "xp_events",
        })

    profile = conn.execute(text("""
        SELECT xp, level_name, status, created_at, updated_at
        FROM progression_profiles
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if profile:
        events.append({
            "date": profile.updated_at.isoformat() if profile.updated_at else None,
            "type": "level_state",
            "title": f"Niveau actuel: {profile.level_name or 'Foundation'}",
            "description": f"Statut de parcours: {profile.status or 'Foundation'}.",
            "impact": "Donne une lecture consolidee de ton avancement White Rock.",
            "xp": int(profile.xp or 0),
            "source": "progression_profiles",
        })
        events.append({
            "date": profile.created_at.isoformat() if profile.created_at else None,
            "type": "profile_created",
            "title": "Parcours White Rock initialise",
            "description": "La progression patrimoniale a commence a etre suivie.",
            "impact": "Cree le point de depart de la trajectoire.",
            "xp": 0,
            "source": "progression_profiles",
        })

    gamification = conn.execute(text("""
        SELECT badges, updated_at
        FROM user_gamification
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if gamification and gamification.badges:
        try:
            if isinstance(gamification.badges, str) and gamification.badges.startswith("["):
                badges = json.loads(gamification.badges)
            else:
                badges = [
                    item.strip()
                    for item in str(gamification.badges).split(",")
                    if item.strip()
                ]
        except Exception:
            badges = []

        if badges:
            events.append({
                "date": gamification.updated_at.isoformat() if gamification.updated_at else None,
                "type": "accomplishments_state",
                "title": f"{len(badges)} accomplissement(s) actifs",
                "description": ", ".join(badges[:5]),
                "impact": "Rend visibles les jalons deja atteints dans le parcours.",
                "xp": 0,
                "source": "user_gamification",
            })

    daily_rows = conn.execute(text("""
        SELECT action_key, action_label, action_title, status, xp_awarded, created_at
        FROM daily_briefing_actions
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 20
    """), {"user_id": user_id}).fetchall()

    for row in daily_rows:
        events.append({
            "date": row.created_at.isoformat() if row.created_at else None,
            "type": "daily_briefing_action",
            "title": row.action_title or row.action_label or _action_label(row.action_key),
            "description": f"Decision quotidienne: {_status_label(row.status)}.",
            "impact": "Transforme le CEO Daily Briefing en action suivie.",
            "xp": int(row.xp_awarded or 0),
            "source": "daily_briefing_actions",
            "status": row.status,
            "status_label": _status_label(row.status),
            "action_key": row.action_key,
        })

    mission_rows = conn.execute(text("""
        SELECT mission_key, status, xp_awarded, completed_at
        FROM mission_progress
        WHERE user_id = :user_id
        ORDER BY completed_at DESC
        LIMIT 20
    """), {"user_id": user_id}).fetchall()

    for row in mission_rows:
        events.append({
            "date": row.completed_at.isoformat() if row.completed_at else None,
            "type": "mission_completed",
            "title": "Mission patrimoniale validee",
            "description": f"Mission {row.mission_key} validee par les donnees backend.",
            "impact": "Un jalon concret de progression a ete atteint.",
            "xp": int(row.xp_awarded or 0),
            "source": "mission_progress",
            "status": row.status,
            "status_label": _status_label(row.status),
            "mission_key": row.mission_key,
        })

    academy_rows = conn.execute(text("""
        SELECT lesson_key, module_key, status, xp_awarded, completed_at
        FROM academy_progress
        WHERE user_id = :user_id
        ORDER BY completed_at DESC
        LIMIT 20
    """), {"user_id": user_id}).fetchall()

    for row in academy_rows:
        events.append({
            "date": row.completed_at.isoformat() if row.completed_at else None,
            "type": "academy_lesson_completed",
            "title": "Lecon Academy validee",
            "description": f"Lecon {row.lesson_key} terminee dans le module {row.module_key or 'academy'}.",
            "impact": "Renforce la comprehension de la prochaine action patrimoniale.",
            "xp": int(row.xp_awarded or 0),
            "source": "academy_progress",
            "status": row.status,
            "status_label": _status_label(row.status),
            "lesson_key": row.lesson_key,
            "module_key": row.module_key,
        })

    task_rows = conn.execute(text("""
        SELECT title, description, mission_key, status, completed_at, created_at
        FROM daily_action_tasks
        WHERE user_id = :user_id
          AND status = 'done'
        ORDER BY completed_at DESC NULLS LAST, created_at DESC
        LIMIT 20
    """), {"user_id": user_id}).fetchall()

    for row in task_rows:
        events.append({
            "date": (row.completed_at or row.created_at).isoformat() if (row.completed_at or row.created_at) else None,
            "type": "daily_task_completed",
            "title": row.title or "Action suivie terminee",
            "description": row.description or "Une tache issue du briefing a ete finalisee.",
            "impact": "Reduit les actions ouvertes et renforce la boucle d'execution.",
            "xp": 30,
            "source": "daily_action_tasks",
            "status": row.status,
            "status_label": _status_label(row.status),
            "mission_key": row.mission_key,
        })

    events = [event for event in events if event.get("date")]
    events.sort(key=lambda item: item.get("date") or "", reverse=True)

    return events[:30]


def build_progression_summary(timeline: list[dict]):
    week_events = timeline[:12]
    decisions = [item for item in week_events if item.get("type") == "daily_briefing_action"]
    missions = [item for item in week_events if item.get("type") == "mission_completed"]
    lessons = [item for item in week_events if item.get("type") == "academy_lesson_completed"]
    tasks = [item for item in week_events if item.get("type") == "daily_task_completed"]
    xp_total = sum(int(item.get("xp") or 0) for item in week_events)

    if missions:
        next_milestone = "Capitaliser sur la mission validee avec une action concrete."
    elif lessons:
        next_milestone = "Transformer la lecon validee en action patrimoniale."
    elif tasks:
        next_milestone = "Choisir la prochaine tache prioritaire dans le briefing."
    elif decisions:
        next_milestone = "Executer la decision enregistree dans le cockpit."
    else:
        next_milestone = "Ouvrir le CEO Daily Briefing et choisir une premiere action."

    return {
        "xp_recent": xp_total,
        "decisions": len(decisions),
        "missions_completed": len(missions),
        "academy_lessons_completed": len(lessons),
        "tasks_completed": len(tasks),
        "next_milestone": next_milestone,
    }


# =========================
# GET USER ID
# =========================
def get_user_identity(conn, email: str):
    row = conn.execute(
        text("""
            SELECT
                users.id,
                users.plan AS user_plan,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
            WHERE users.email = :email
        """),
        {"email": email}
    ).fetchone()

    if not row:
        return None

    return {
        "id": row.id,
        "plan": resolve_effective_plan(
            row.user_plan,
            row.subscription_plan,
            row.subscription_status,
        ),
    }


# =========================
# READ ONLY GAMIFICATION API (CACHE OPTIMIZED)
# =========================
@router.get("")
@router.get("/")
@router.get("/gamification")
def get_gamification(user=Depends(get_current_user)):

    email = user.get("email") if isinstance(user, dict) else user

    with engine.begin() as conn:

        identity = get_user_identity(conn, email)
        user_id = identity["id"] if identity else None
        plan = identity["plan"] if identity else "FREE"
        cache_key = f"gamification:{email}:{plan}"

        cached = get_cache(cache_key)
        if cached:
            return cached

        # =========================
        # FALLBACK SAFE RESPONSE
        # =========================
        default_response = {
            "xp": 0,
            "level": 1,
            "streak": 0,
            "badges": [],
            "actions": build_gamification_actions(0, "FREE"),
            "upgrade": build_upgrade(0, "FREE", plan),
            "ai_coach": {
                "message": "Ajoute tes donnees pour recevoir des affiliations pertinentes.",
                "affiliations": [],
            },
        }
        default_response = stamp_state(default_response)

        if not user_id:
            set_cache(cache_key, default_response, ttl=60)
            return default_response

        ensure_gamification_tables(conn)

        row = conn.execute(
            text("""
                SELECT xp, level, streak, badges
                FROM user_gamification
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not row:
            default_response["ai_coach"]["affiliations"] = build_affiliations(conn, user_id)
            default_response = stamp_state(default_response)
            set_cache(cache_key, default_response, ttl=60)
            return default_response

        # =========================
        # SAFE BADGES PARSING
        # =========================
        badges = []

        try:
            if row.badges:
                # support JSON OR CSV
                if isinstance(row.badges, str):
                    if row.badges.startswith("["):
                        badges = json.loads(row.badges)
                    else:
                        badges = [b.strip() for b in row.badges.split(",") if b.strip()]
        except:
            badges = []

        result = {
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.streak or 0,
            "badges": badges,
            "actions": build_gamification_actions(row.xp or 0, row.level or 1),
            "upgrade": build_upgrade(row.xp or 0, row.level or 1, plan),
            "ai_coach": {
                "message": (
                    "Je te propose les prochaines actions et affiliations en "
                    "fonction de ta situation, de ton score et de tes objectifs."
                ),
                "affiliations": build_affiliations(conn, user_id),
            }
        }
        result = stamp_state(result)

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result


@router.get("/progression-timeline")
def get_progression_timeline(user=Depends(get_current_user)):
    email = user.get("email") if isinstance(user, dict) else user

    with engine.begin() as conn:
        identity = get_user_identity(conn, email)
        user_id = identity["id"] if identity else None
        plan = identity["plan"] if identity else "FREE"

        if not user_id:
            return {
                "version": "progression-timeline-v1",
                "plan": plan,
                "timeline": [],
                "summary": build_progression_summary([]),
            }

        timeline = build_progression_timeline(conn, user_id)
        summary = build_progression_summary(timeline)

        return {
            "version": "progression-timeline-v1",
            "plan": plan,
            "timeline": timeline,
            "summary": summary,
        }
