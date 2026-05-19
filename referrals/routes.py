import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine


router = APIRouter()
_referral_schema_ready = False


def ensure_referral_tables(conn):
    global _referral_schema_ready

    if _referral_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_referrals (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            referral_code TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS referral_events (
            id SERIAL PRIMARY KEY,
            referrer_user_id INTEGER NOT NULL,
            referred_email TEXT,
            referred_user_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            reward_xp INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            converted_at TIMESTAMP
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS referral_rewards (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            reward_type TEXT NOT NULL,
            value TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            redeemed_at TIMESTAMP
        )
    """))

    _referral_schema_ready = True


def generate_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_or_create_code(conn, user_id: int) -> str:
    row = conn.execute(text("""
        SELECT referral_code
        FROM user_referrals
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if row:
        return row.referral_code

    for _ in range(5):
        code = generate_code()
        try:
            conn.execute(text("""
                INSERT INTO user_referrals (user_id, referral_code)
                VALUES (:user_id, :code)
            """), {"user_id": user_id, "code": code})
            return code
        except Exception:
            continue

    raise HTTPException(status_code=500, detail="Unable to create referral code")


@router.get("/me")
def get_referral_dashboard(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        ensure_referral_tables(conn)
        user_id = get_user_id(conn, email)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        code = get_or_create_code(conn, user_id)

        stats = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'converted') AS converted,
                COALESCE(SUM(reward_xp), 0) AS reward_xp
            FROM referral_events
            WHERE referrer_user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        rewards = conn.execute(text("""
            SELECT reward_type, value, status, created_at
            FROM referral_rewards
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 10
        """), {"user_id": user_id}).fetchall()

    return {
        "referral_code": code,
        "referral_url": f"https://vision-business.com/?ref={code}",
        "stats": {
            "invites": int(stats.total or 0),
            "converted": int(stats.converted or 0),
            "reward_xp": int(stats.reward_xp or 0),
        },
        "rewards": [
            {
                "type": row.reward_type,
                "value": row.value,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rewards
        ],
    }


@router.post("/track")
def track_referral(data: dict):
    code = str(data.get("referral_code") or data.get("code") or "").strip().upper()
    referred_email = data.get("email")

    if not code:
        raise HTTPException(status_code=400, detail="referral_code required")

    with engine.begin() as conn:
        ensure_referral_tables(conn)
        referrer = conn.execute(text("""
            SELECT user_id
            FROM user_referrals
            WHERE referral_code = :code
        """), {"code": code}).fetchone()

        if not referrer:
            raise HTTPException(status_code=404, detail="Referral code not found")

        conn.execute(text("""
            INSERT INTO referral_events (referrer_user_id, referred_email, status)
            VALUES (:referrer_user_id, :referred_email, 'pending')
        """), {
            "referrer_user_id": referrer.user_id,
            "referred_email": referred_email,
        })

    return {"status": "tracked"}
