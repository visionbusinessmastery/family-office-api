# =========================
# LOG ENGINE V4 (DB)
# =========================

from sqlalchemy import text
from database import engine


def log_event(user_email, actions, strategy, score):

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO autopilot_events (
                user_email, actions, strategy, score
            )
            VALUES (:email, :actions, :strategy, :score)
        """), {
            "email": user_email,
            "actions": str(actions),
            "strategy": str(strategy),
            "score": str(score)
        })


def get_logs(user_email):

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT timestamp, actions, strategy, score
            FROM autopilot_events
            WHERE user_email = :email
            ORDER BY timestamp DESC
            LIMIT 50
        """), {"email": user_email}).fetchall()

    return [dict(r._mapping) for r in rows]
