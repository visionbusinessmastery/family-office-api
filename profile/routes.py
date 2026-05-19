from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
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
            avatar_url TEXT,
            goals TEXT,
            horizon TEXT,
            investor_profile TEXT,
            risk_level TEXT,
            main_currency TEXT DEFAULT 'EUR',
            motivation TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    _profile_schema_ready = True


def row_to_profile(row):
    if not row:
        return {
            "first_name": None,
            "avatar_url": None,
            "goals": [],
            "horizon": None,
            "investor_profile": None,
            "risk_level": None,
            "main_currency": "EUR",
            "motivation": None,
        }

    goals = [item for item in (row.goals or "").split("|") if item]

    return {
        "first_name": row.first_name,
        "avatar_url": row.avatar_url,
        "goals": goals,
        "horizon": row.horizon,
        "investor_profile": row.investor_profile,
        "risk_level": row.risk_level,
        "main_currency": row.main_currency or "EUR",
        "motivation": row.motivation,
    }


@router.get("/me")
def get_profile(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_profile_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        row = conn.execute(text("""
            SELECT first_name, avatar_url, goals, horizon, investor_profile,
                   risk_level, main_currency, motivation
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
                user_id, first_name, avatar_url, goals, horizon,
                investor_profile, risk_level, main_currency, motivation, updated_at
            )
            VALUES (
                :user_id, :first_name, :avatar_url, :goals, :horizon,
                :investor_profile, :risk_level, :main_currency, :motivation, NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                first_name = EXCLUDED.first_name,
                avatar_url = EXCLUDED.avatar_url,
                goals = EXCLUDED.goals,
                horizon = EXCLUDED.horizon,
                investor_profile = EXCLUDED.investor_profile,
                risk_level = EXCLUDED.risk_level,
                main_currency = EXCLUDED.main_currency,
                motivation = EXCLUDED.motivation,
                updated_at = NOW()
        """), {
            "user_id": user_id,
            "first_name": data.get("first_name"),
            "avatar_url": data.get("avatar_url"),
            "goals": goals_text,
            "horizon": data.get("horizon"),
            "investor_profile": data.get("investor_profile"),
            "risk_level": data.get("risk_level"),
            "main_currency": data.get("main_currency") or "EUR",
            "motivation": data.get("motivation"),
        })

    return {"status": "ok"}
