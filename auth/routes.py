import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets
import os

from database import engine
from auth.utils import hash_password
from auth.schemas import UserAuth
from auth.email_service import send_verification_email

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    raise Exception("Missing STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# =========================
# REGISTER (EMAIL ONLY)
# =========================
@router.post("/register")
def register(data: UserAuth, request: Request):

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

        # =========================
        # CREATE USER (NO PASSWORD YET)
        # =========================
        result = conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified, verification_attempts)
            VALUES (:email, NULL, FALSE, 0)
            RETURNING id
        """), {
            "email": email
        })

        user_id = result.fetchone()[0]

        # =========================
        # TOKEN
        # =========================
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

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
                NOW(),
                :expires_at
            )
        """), {
            "email": email,
            "token": token,
            "expires_at": expires_at
        })

        # increment attempts
        conn.execute(text("""
            UPDATE users
            SET verification_attempts = verification_attempts + 1
            WHERE email = :email
        """), {"email": email})

    # =========================
    # SEND EMAIL
    # =========================
    send_verification_email(email, token)

    return {
        "message": "User created",
        "user_id": user_id,
        "verification_required": True
    }
