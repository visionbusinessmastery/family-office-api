from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import delete_cache_patterns
from database import engine


router = APIRouter()
_profile_schema_ready = False


def ensure_profile_tables(conn):
    global _profile_schema_ready

    if _profile_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_wealth_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            first_name TEXT,
            bio TEXT,
            avatar_url TEXT,
            goals TEXT,
            horizon TEXT,
            investor_profile TEXT,
            risk_level TEXT,
            main_currency TEXT DEFAULT 'EUR',
            motivation TEXT,
            has_children BOOLEAN DEFAULT FALSE,
            transmission_goal TEXT,
            expatriation_interest TEXT,
            governance_need TEXT,
            confidentiality_need TEXT,
            family_strategy TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS bio TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS has_children BOOLEAN DEFAULT FALSE"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS transmission_goal TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS expatriation_interest TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS governance_need TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS confidentiality_need TEXT"))
    conn.execute(text("ALTER TABLE user_wealth_profiles ADD COLUMN IF NOT EXISTS family_strategy TEXT"))

    _profile_schema_ready = True


def row_to_profile(row):
    if not row:
        return {
            "first_name": None,
            "bio": None,
            "avatar_url": None,
            "goals": [],
            "horizon": None,
            "investor_profile": None,
            "risk_level": None,
            "main_currency": "EUR",
            "motivation": None,
            "has_children": False,
            "transmission_goal": None,
            "expatriation_interest": None,
            "governance_need": None,
            "confidentiality_need": None,
            "family_strategy": None,
        }

    goals = [item for item in (row.goals or "").split("|") if item]

    return {
        "first_name": row.first_name,
        "bio": row.bio,
        "avatar_url": row.avatar_url,
        "goals": goals,
        "horizon": row.horizon,
        "investor_profile": row.investor_profile,
        "risk_level": row.risk_level,
        "main_currency": row.main_currency or "EUR",
        "motivation": row.motivation,
        "has_children": bool(row.has_children),
        "transmission_goal": row.transmission_goal,
        "expatriation_interest": row.expatriation_interest,
        "governance_need": row.governance_need,
        "confidentiality_need": row.confidentiality_need,
        "family_strategy": row.family_strategy,
    }


@router.get("/me")
def get_profile(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        row = conn.execute(text("""
            SELECT first_name, bio, avatar_url, goals, horizon, investor_profile,
                   risk_level, main_currency, motivation, has_children,
                   transmission_goal, expatriation_interest, governance_need,
                   confidentiality_need, family_strategy
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

    return {"profile": row_to_profile(row)}


@router.put("/me")
def update_profile(data: dict, email: str = Depends(get_current_user)):
    goals = data.get("goals") or []

    if isinstance(goals, str):
        goals_text = goals
    else:
        goals_text = "|".join(str(goal) for goal in goals if goal)

    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(text("""
            INSERT INTO user_wealth_profiles (
                user_id, first_name, bio, avatar_url, goals, horizon,
                investor_profile, risk_level, main_currency, motivation,
                has_children, transmission_goal, expatriation_interest,
                governance_need, confidentiality_need, family_strategy, updated_at
            )
            VALUES (
                :user_id, :first_name, :bio, :avatar_url, :goals, :horizon,
                :investor_profile, :risk_level, :main_currency, :motivation,
                :has_children, :transmission_goal, :expatriation_interest,
                :governance_need, :confidentiality_need, :family_strategy, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                first_name = EXCLUDED.first_name,
                bio = EXCLUDED.bio,
                avatar_url = EXCLUDED.avatar_url,
                goals = EXCLUDED.goals,
                horizon = EXCLUDED.horizon,
                investor_profile = EXCLUDED.investor_profile,
                risk_level = EXCLUDED.risk_level,
                main_currency = EXCLUDED.main_currency,
                motivation = EXCLUDED.motivation,
                has_children = EXCLUDED.has_children,
                transmission_goal = EXCLUDED.transmission_goal,
                expatriation_interest = EXCLUDED.expatriation_interest,
                governance_need = EXCLUDED.governance_need,
                confidentiality_need = EXCLUDED.confidentiality_need,
                family_strategy = EXCLUDED.family_strategy,
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "first_name": data.get("first_name"),
            "bio": data.get("bio"),
            "avatar_url": data.get("avatar_url"),
            "goals": goals_text,
            "horizon": data.get("horizon"),
            "investor_profile": data.get("investor_profile"),
            "risk_level": data.get("risk_level"),
            "main_currency": data.get("main_currency") or "EUR",
            "motivation": data.get("motivation"),
            "has_children": bool(data.get("has_children")),
            "transmission_goal": data.get("transmission_goal"),
            "expatriation_interest": data.get("expatriation_interest"),
            "governance_need": data.get("governance_need"),
            "confidentiality_need": data.get("confidentiality_need"),
            "family_strategy": data.get("family_strategy"),
        })

    delete_cache_patterns(
        f"intel:{email}*",
        f"context:{email}*",
        f"product:{email}*",
        f"advisor:{email}*",
    )

    return {"status": "ok"}
