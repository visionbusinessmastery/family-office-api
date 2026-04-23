from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import uuid


def generate_verification_token():
    return str(uuid.uuid4())


def save_verification_token(email: str, token: str):

    expires = datetime.utcnow() + timedelta(hours=24)

    with engine.begin() as conn:

        # invalidate old tokens
        conn.execute(text("""
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE email = :email AND is_used = FALSE
        """), {"email": email})

        # insert new token
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

    print("📧 TOKEN SAVED:", email, token)

    return {
        "email": email,
        "token": token,
        "expires_at": expires
    }
