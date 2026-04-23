from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import uuid


# =========================
# GENERATE TOKEN
# =========================
def generate_verification_token():
    return str(uuid.uuid4())


# =========================
# SAVE TOKEN (FIXED)
# =========================
def save_verification_token(email: str, token: str):

    expires = datetime.utcnow() + timedelta(hours=24)

    with engine.begin() as conn:

        # =========================
        # CLEAN OLD TOKENS (IMPORTANT)
        # =========================
        conn.execute(text("""
            DELETE FROM email_verifications
            WHERE email = :email
        """), {"email": email})

        # =========================
        # INSERT NEW TOKEN
        # =========================
        conn.execute(text("""
            INSERT INTO email_verifications (
                email,
                token,
                is_used,
                created_at,
                expires_at
            )
            VALUES (
                :email,
                :token,
                FALSE,
                :created_at,
                :expires_at
            )
        """), {
            "email": email,
            "token": token,
            "created_at": datetime.utcnow(),
            "expires_at": expires
        })
