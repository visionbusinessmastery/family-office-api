# =========================
# IMPORTS
# =========================
from sqlalchemy import text


# =========================
# UNLOCK BADGES
# =========================
def unlock_badges(conn, user_id: int):

    rows = conn.execute(
        text("""
            SELECT COUNT(*) as total
            FROM finance_items
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    ).fetchone()

    total = rows.total if rows else 0

    badges = []

    if total >= 1:
        badges.append("Premier revenu")

    if total >= 10:
        badges.append("Analyste")

    if total >= 50:
        badges.append("Investisseur actif")

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
