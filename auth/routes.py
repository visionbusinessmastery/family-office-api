import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets
import os

from database import engine
from auth.utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user,
    build_unlocks
)

from auth.schemas import (
    UserAuth,
    UserProfileRequest,
    SetPasswordRequest
)

from intelligence.analyzers.family_office_score import compute_family_office_score
from auth.email_service import send_verification_email

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    raise Exception("Missing STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# =========================
# REGISTER
# =========================
@router.post("/register")
def register(data: UserAuth):

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

        # CREATE USER
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

        # TOKEN
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        conn.execute(text("""
            INSERT INTO email_verifications (
                user_id,
                email,
                token,
                expires_at,
                is_used
            )
            VALUES (
                :user_id,
                :email,
                :token,
                :expires_at,
                FALSE
            )
        """), {
            "user_id": user_id,
            "email": email,
            "token": token,
            "expires_at": expires_at
        })

    # =========================
    # SEND EMAIL (IMPORTANT FIX)
    # =========================
    send_verification_email(email, token)

    return {
        "message": "User created",
        "user_id": user_id,
        "verification_required": True
    }


# =========================
# VERIFY EMAIL
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

        print("EMAIL:", email)
        print("EXPIRES:", expires_at)
        print("USED:", is_used)

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
