# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

router = APIRouter()


# =========================
# GET USER ID
# =========================
def get_user_id(conn, email: str):

    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return row.id if row else None


# =========================
# READ GAMIFICATION ONLY
# =========================
@router.get("/gamification")
def get_gamification(user=Depends(get_current_user)):

    email = user.get("email") if isinstance(user, dict) else user

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {
                "xp": 0,
                "level": 1,
                "streak": 0,
                "badges": []
            }

        row = conn.execute(
            text("""
                SELECT xp, level, streak, badges
                FROM user_gamification
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not row:
            return {
                "xp": 0,
                "level": 1,
                "streak": 0,
                "badges": []
            }

        return {
            "xp": row.xp or 0,
            "level": row.level or 1,
            "streak": row.streak or 0,
            "badges": row.badges.split(",") if row.badges else []
        }
