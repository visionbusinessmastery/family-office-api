from fastapi import APIRouter, Depends
from auth.utils import get_current_user

@router.get("/gamification")
def get_gamification(user=Depends(get_current_user)):

    email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

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
            "xp": row.xp,
            "level": row.level,
            "streak": row.streak,
            "badges": row.badges.split(",") if row.badges else []
        }

def unlock_badges(conn, user_id):

    rows = conn.execute(
        text("""
            SELECT COUNT(*) as total
            FROM finance_items
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    badges = []

    if rows.total >= 1:
        badges.append("Premier revenu")

    if rows.total >= 10:
        badges.append("Analyste")

    conn.execute(
        text("""
            UPDATE user_gamification
            SET badges = :badges
            WHERE user_id = :user_id
        """),
        {
            "badges": ",".join(badges),
            "user_id": user_id
        }
    )
