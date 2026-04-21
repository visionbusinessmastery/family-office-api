import uuid
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
