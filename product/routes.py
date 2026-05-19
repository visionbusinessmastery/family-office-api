from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from intelligence.user_intelligence_engine import compute_user_intelligence
from product.entitlements import (
    MODULE_REGISTRY,
    build_entitlements,
    can_access_module,
    normalize_plan,
    plan_allows,
    resolve_effective_plan,
)


router = APIRouter()
_product_schema_ready = False


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

    _product_schema_ready = True


def safe_count(conn, query: str, params: dict):
    try:
        return int(conn.execute(text(query), params).scalar() or 0)
    except Exception:
        return 0


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

    completed_steps = sum([
        finance_count > 0,
        portfolio_count > 0,
        real_estate_count > 0,
        yield_count > 0,
        venture_count > 0,
    ])

    return {
        "finance_count": finance_count,
        "portfolio_count": portfolio_count,
        "real_estate_count": real_estate_count,
        "yield_count": yield_count,
        "venture_count": venture_count,
        "completed_steps": completed_steps,
        "completion_percent": round((completed_steps / 5) * 100),
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
            locked.append({
                **item,
                "state": "locked",
                "reason": (
                    f"Plan {module['min_plan']} requis"
                    if normalize_plan(plan) != normalize_plan(module["min_plan"])
                    else f"Score {module['min_score']} requis"
                ),
            })

    return {"visible": visible, "locked": locked}


def build_missions(data_profile: dict, score: int, plan: str):
    missions = []

    if data_profile["finance_count"] == 0:
        missions.append({
            "key": "complete_finance",
            "title": "Completer ton cashflow",
            "description": "Ajoute revenus, charges, epargne et dettes pour clarifier tes fondations.",
            "xp": 100,
            "module": "finance",
        })

    if data_profile["portfolio_count"] == 0:
        missions.append({
            "key": "add_first_asset",
            "title": "Ajouter ton premier actif",
            "description": "C'est le premier pas vers une vision patrimoniale centralisee.",
            "xp": 120,
            "module": "portfolio",
        })

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

    return missions[:3]


@router.get("/context")
def product_context(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        plan_row = conn.execute(text("""
            SELECT
                users.plan AS user_plan,
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
        missions = build_missions(data_profile, score, plan)

    return {
        "plan": plan,
        "score": score,
        "entitlements": entitlements,
        "progression": progression,
        "data_profile": data_profile,
        "modules": modules,
        "missions": missions,
    }
