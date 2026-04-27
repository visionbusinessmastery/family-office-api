import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets
import os

from database import engine
from auth.schemas import UserAuth, SetPasswordRequest
from auth.utils import hash_password, create_token, get_current_user
from auth.email_service import send_verification_email

router = APIRouter()

# =========================
# CONFIG
# =========================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

if not stripe.api_key:
    raise Exception("Missing STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# =========================
# REGISTER (FINAL CLEAN SYNC FRONTEND)
# =========================
@router.post("/register")
def register(data: UserAuth, request: Request):

    email = data.email.lower()

    try:
        with engine.begin() as conn:

            existing = conn.execute(text("""
                SELECT id, is_verified FROM users WHERE email = :email
            """), {"email": email}).fetchone()

            # =========================
            # USER EXISTS
            # =========================
            if existing:

                # 🔐 USER VERIFIED → LOGIN
                if existing.is_verified:
                    return {
                        "status": "success",
                        "action": "login",
                        "message": "Compte déjà existant"
                    }

                # 🔁 USER NOT VERIFIED → RESEND EMAIL
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=24)

                conn.execute(text("""
                    INSERT INTO email_verifications (
                        email, token, is_used, created_at, expires_at
                    )
                    VALUES (
                        :email, :token, FALSE, NOW(), :expires_at
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

                send_verification_email(email, token)

                return {
                    "status": "success",
                    "action": "resend_verification",
                    "message": "Email déjà enregistré. Vérifie ta boîte mail."
                }

            # =========================
            # CREATE USER
            # =========================
            result = conn.execute(text("""
                INSERT INTO users (
                    email, password_hash, is_verified, verification_attempts
                )
                VALUES (
                    :email, NULL, FALSE, 0
                )
                RETURNING id
            """), {"email": email})

            user_id = result.fetchone()[0]

            # =========================
            # CREATE TOKEN
            # =========================
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)

            conn.execute(text("""
                INSERT INTO email_verifications (
                    email, token, is_used, created_at, expires_at
                )
                VALUES (
                    :email, :token, FALSE, NOW(), :expires_at
                )
            """), {
                "email": email,
                "token": token,
                "expires_at": expires_at
            })

        # =========================
        # SEND EMAIL (OUTSIDE TRANSACTION)
        # =========================
        send_verification_email(email, token)

        return {
            "status": "success",
            "action": "verify_email",
            "message": "Compte créé. Vérifie ton email.",
            "user_id": user_id,
            "verification_required": True
        }

    except Exception as e:
        print("REGISTER ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Erreur serveur register")
        

# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(token: str):

    with engine.begin() as conn:

        record = conn.execute(text("""
            SELECT email FROM email_verifications
            WHERE token = :token
            AND is_used = FALSE
            AND expires_at > NOW()
        """), {"token": token}).fetchone()

        if not record:
            raise HTTPException(status_code=400, detail="Token invalide")

        email = record.email

        # mark used
        conn.execute(text("""
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE token = :token
        """), {"token": token})

        # verify user
        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE
            WHERE email = :email
        """), {"email": email})

    return {
        "message": "Email verified",
        "email": email
    }

# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    email = data.email.lower()
    password_hash = hash_password(data.password)

    with engine.begin() as conn:

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password
            WHERE email = :email
        """), {
            "email": email,
            "password": password_hash
        })

    token = create_token({"sub": email})

    return {
        "message": "Password set",
        "access_token": token
    }

# =========================
# ME
# =========================
@router.get("/me")
def get_me(email: str = get_current_user):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT email, plan, profile_completed
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        return dict(user)

# =========================
# ONBOARDING SAVE
# =========================
@router.post("/onboarding/save")
def save_onboarding(data: dict, email: str = get_current_user):

    with engine.begin() as conn:

        conn.execute(text("""
            UPDATE users
            SET profile_completed = TRUE
            WHERE email = :email
        """), {"email": email})

    return {"status": "ok"}

# =========================
# PLAN UPDATE
# =========================
@router.post("/plan/update")
def update_plan(plan: str, email: str = get_current_user):

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users SET plan = :plan WHERE email = :email
        """), {"plan": plan, "email": email})

    return {"status": "updated"}
