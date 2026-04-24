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

from auth.schemas import UserAuth
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
def register(data: UserAuth, request: Request):

    email = data.email.lower()
    ip = request.client.host

    with engine.begin() as conn:

        # =========================
        # RATE LIMIT IP (SIMPLE)
        # =========================
        ip_check = conn.execute(text("""
            SELECT COUNT(*) 
            FROM email_verifications
            WHERE created_at > NOW() - INTERVAL '10 minutes'
        """)).scalar()

        if ip_check and ip_check > 10:
            raise HTTPException(429, "Too many requests, try later")

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
        # CREATE USER
        # =========================
        hashed_password = hash_password(data.password)

        result = conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified, verification_attempts)
            VALUES (:email, :password_hash, FALSE, 0)
            RETURNING id
        """), {
            "email": email,
            "password_hash": hashed_password
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


# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(token: str = None):

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
            return {"status": "already_verified", "email": email}

        if expires_at < datetime.utcnow():
            raise HTTPException(400, "Token expired")

        # mark token used
        conn.execute(text("""
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE token = :token
        """), {"token": token})

        # update user
        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE,
                email_verified_at = NOW()
            WHERE email = :email
        """), {"email": email})

    return {"status": "verified", "email": email}


# =========================
# EMAIL STATUS
# =========================
@router.get("/email-status")
def email_status(email: str):

    email = email.lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT is_verified, email_verified_at, verification_attempts
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        return {
            "email": email,
            "verified": user.is_verified,
            "verified_at": user.email_verified_at,
            "attempts": user.verification_attempts,
            "status": "verified" if user.is_verified else "pending"
        }


# =========================
# RESEND EMAIL
# =========================
@router.post("/resend-verification")
def resend_verification(data: dict):

    email = data.get("email", "").lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT is_verified, verification_attempts
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        if user.is_verified:
            return {"message": "Already verified"}

        if user.verification_attempts >= 5:
            raise HTTPException(429, "Too many attempts")

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

        conn.execute(text("""
            UPDATE users
            SET verification_attempts = verification_attempts + 1
            WHERE email = :email
        """), {"email": email})

    send_verification_email(email, token)

    return {"message": "Email resent"}

