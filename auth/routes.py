import stripe
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets
import os

from database import engine
from auth.utils import hash_password
from auth.email_service import send_verification_email

from auth.verification import save_verification_token, generate_verification_token

router = APIRouter()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# =========================
# REGISTER (FIX FINAL)
# =========================
@router.post("/register")
def register(data):

    email = data.email.lower()

    with engine.begin() as conn:

        existing = conn.execute(text("""
            SELECT id, is_verified FROM users WHERE email = :email
        """), {"email": email}).fetchone()

        if existing:

            if not existing.is_verified:
                return {
                    "message": "User exists but not verified",
                    "action": "resend_verification"
                }

            return {
                "message": "User already exists",
                "action": "login"
            }

        hashed_password = hash_password(data.password)

        result = conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified)
            VALUES (:email, :password_hash, FALSE)
            RETURNING id
        """), {
            "email": email,
            "password_hash": hashed_password
        })

        user_id = result.fetchone()[0]

        # =========================
        # TOKEN CLEAN (UUID UNIQUE)
        # =========================
        token = generate_verification_token()

        save_verification_token(email, token)
       
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
            "expires_at": expires_at
        })

    # =========================
    # SEND EMAIL (CRUCIAL FIX)
    # =========================
    send_verification_email(email, token)

    return {
        "message": "User created",
        "user_id": user_id,
        "verification_required": True
    }


# =========================
# VERIFY EMAIL (OK FINAL)
# =========================
@router.get("/verify-email")
def verify_email(token: str = None):

    print("VERIFY TOKEN RECEIVED:", token)

    if not token:
        raise HTTPException(400, "Missing token")

    with engine.begin() as conn:

        record = conn.execute(text("""
            SELECT email, expires_at, is_used
            FROM email_verifications
            WHERE token = :token
        """), {"token": token}).fetchone()

        if not record:
            raise HTTPException(400, "Invalid token")

        email, expires_at, is_used = record

        if is_used:
            return {"status": "already_verified"}

        if expires_at < datetime.utcnow():
            raise HTTPException(400, "Token expired")

        conn.execute(text("""
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE token = :token
        """), {"token": token})

        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE
            WHERE email = :email
        """), {"email": email})

    return {"status": "verified", "email": email}
