import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine


# =========================
# TOKEN VERIFICATION
# =========================
def generate_verification_token():
    return str(uuid.uuid4())


# =========================
# SAVE TOKEN VERIFICATION
# =========================
def save_verification_token(email: str, token: str):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users
            SET verification_token=:token
            WHERE email=:email
        """), {"email": email, "token": token})


# =========================
# EMAIL TOKEN VERIFICATION
# =========================
def verify_email_token(token: str):
    with engine.begin() as conn:
        user = conn.execute(text("""
            SELECT email FROM users
            WHERE verification_token=:token
        """), {"token": token}).fetchone()

        if not user:
            return None

        conn.execute(text("""
            UPDATE users
            SET email_verified=true,
                verification_token=NULL
            WHERE email=:email
        """), {"email": user[0]})

        return user[0]


# =========================
# EMAIL VERIFICATION
# =========================
def create_email_verification(email: str):
    token = str(uuid.uuid4())
    expires = datetime.utcnow() + timedelta(minutes=30)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO email_verifications (email, token, expires_at)
            VALUES (:email, :token, :expires_at)
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

    return token
