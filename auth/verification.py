from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import uuid


# =========================
# TOKEN VERIFICATION
# =========================
def generate_verification_token():
    return str(uuid.uuid4())


# =========================
# SAVE TOKEN VERIFICATION
# =========================
def save_verification_token(email: str, token: str):
    expires = datetime.utcnow() + timedelta(hours=24)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO email_verifications (email, token, verified, created_at, expires_at)
            VALUES (:email, :token, FALSE, NOW(), :expires_at)
            ON CONFLICT (email)
            DO UPDATE SET
                token = EXCLUDED.token,
                expires_at = EXCLUDED.expires_at,
                verified = FALSE
        """), {
            "email": email,
            "token": token,
            "expires_at": expires
        })

