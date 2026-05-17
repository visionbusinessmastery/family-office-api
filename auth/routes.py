# =========================
# IMPORTS
# =========================
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text

from database import engine
from auth.schemas import UserAuth, SetPasswordRequest, LoginRequest
from auth.utils import (
    hash_password,
    create_token,
    get_current_user,
    verify_password
)
from auth.email_service import send_verification_email
from core.cache import redis_client

router = APIRouter()

# =========================
# INVALIDATE USER
# =========================
def invalidate_user_intelligence_caches(email: str):
    try:
        if not redis_client:
            return

        redis_client.delete(
            f"intel:{email}",
            f"context:{email}",
            f"score:{email}",
        )
    except Exception:
        pass



# =========================
# REGISTER
# =========================
@router.post("/register")
def register(data: UserAuth):

    email = data.email.lower()

    try:
        with engine.begin() as conn:

            existing = conn.execute(text("""
                SELECT id, is_verified FROM users WHERE email = :email
            """), {"email": email}).fetchone()

            if existing:

                if existing.is_verified:
                    return {
                        "status": "success",
                        "action": "login"
                    }

                token = secrets.token_urlsafe(32)

                conn.execute(text("""
                    INSERT INTO email_verifications (
                        email, token, is_used, created_at, expires_at
                    )
                    VALUES (
                        :email, :token, FALSE, NOW(), NOW() + interval '24 hours'
                    )
                """), {"email": email, "token": token})

                send_verification_email(email, token)

                return {"status": "success", "action": "resend_verification"}

            result = conn.execute(text("""
                INSERT INTO users (email, is_verified, verification_attempts, profile_completed)
                VALUES (:email, FALSE, 0, FALSE)
                RETURNING id
            """), {"email": email})

            user_id = result.fetchone()[0]

            token = secrets.token_urlsafe(32)

            conn.execute(text("""
                INSERT INTO email_verifications (
                    email, token, is_used, created_at, expires_at
                )
                VALUES (
                    :email, :token, FALSE, NOW(), NOW() + interval '24 hours'
                )
            """), {"email": email, "token": token})

        send_verification_email(email, token)

        return {
            "status": "success",
            "action": "verify_email",
            "user_id": user_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        conn.execute(text("""
            UPDATE email_verifications SET is_used = TRUE WHERE token = :token
        """), {"token": token})

        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE,
                profile_completed = FALSE
            WHERE email = :email
        """), {"email": email})

    return {"email": email}


# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    email = data.email.lower()
    password_hash = hash_password(data.password)

    with engine.begin() as conn:

        result = conn.execute(text("""
            UPDATE users
            SET password_hash = :password
            WHERE email = :email
        """), {"email": email, "password": password_hash})

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="Utilisateur introuvable")

    token = create_token({"sub": email})

    return {"access_token": token}


# =========================
# ME (STATE RECOVERY SAFE)
# =========================
@router.get("/me")
def get_me(email: str = Depends(get_current_user)):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT email, plan, profile_completed, revenus_mensuels, charges_mensuelles
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # =========================
        # 🛡️ STATE RECOVERY LOGIC
        # =========================
        profile_completed = bool(user.profile_completed)

        data = {
            "email": user.email,
            "plan": user.plan,
            "profile_completed": profile_completed,
            "revenus_mensuels": user.revenus_mensuels or 0,
            "charges_mensuelles": user.charges_mensuelles or 0,
        }

        if not profile_completed:
            data["state"] = "ONBOARDING_REQUIRED"
        else:
            data["state"] = "READY"

        return data

# =========================
# LOGIN
# =========================
@router.post("/login")
def login(data: LoginRequest):

    email = data.email.lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT password_hash FROM users WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Utilisateur introuvable")

        if user.password_hash is None:
            return {"action": "set_password_required"}

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Mot de passe incorrect")

    token = create_token({"sub": email})

    return {"access_token": token}


# =========================
# ONBOARDING (IMPORTANT FIX)
# =========================
@router.post("/onboarding/save")
def save_onboarding(data: dict, email: str = Depends(get_current_user)):

    with engine.begin() as conn:

        result = conn.execute(text("""
            UPDATE users
            SET
                age = :age,
                situation_pro = :situation_pro,
                revenus_mensuels = :revenus_mensuels,
                charges_mensuelles = :charges_mensuelles,
                profile_completed = TRUE
            WHERE email = :email
        """), {
            "email": email,
            "age": data.get("age"),
            "situation_pro": data.get("situation_pro"),
            "revenus_mensuels": data.get("revenus_mensuels"),
            "charges_mensuelles": data.get("charges_mensuelles"),
        })

        if result.rowcount == 0:
            raise HTTPException(status_code=400, detail="Onboarding failed")
        
        invalidate_user_intelligence_caches(email)
        
    return {"status": "ok"}


# =========================
# PLAN UPDATE
# =========================
@router.post("/plan/update")
def update_plan(plan: str, email: str = Depends(get_current_user)):

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users SET plan = :plan WHERE email = :email
        """), {"plan": plan, "email": email})

    return {"status": "updated"}


# =========================
# ONBOARDING COMPLETE
# =========================
@router.post("/onboarding/complete")
def complete_onboarding(data: dict, email: str = Depends(get_current_user)):

    with engine.begin() as conn:

        result = conn.execute(text("""
            UPDATE users
            SET
                age = :age,
                situation_pro = :situation_pro,
                revenus_mensuels = :revenus_mensuels,
                charges_mensuelles = :charges_mensuelles,
                profile_completed = TRUE
            WHERE email = :email
        """), {
            "email": email,
            "age": data.get("age"),
            "situation_pro": data.get("situation_pro"),
            "revenus_mensuels": data.get("revenus_mensuels"),
            "charges_mensuelles": data.get("charges_mensuelles"),
        })

        if result.rowcount == 0:
            return {"error": "onboarding failed"}

        invalidate_user_intelligence_caches(email)
        
    return {"status": "completed"}


# =========================
# UPDATE ONBOARDING (CLEAN FINAL VERSION)
# =========================
@router.put("/onboarding/update")
def update_onboarding(data: dict, email: str = Depends(get_current_user)):

    with engine.begin() as conn:

        conn.execute(text("""
            UPDATE users
            SET revenus_mensuels = :revenus_mensuels,
                charges_mensuelles = :charges_mensuelles
            WHERE email = :email
        """), {
            "email": email,
            "revenus_mensuels": data.get("revenus_mensuels"),
            "charges_mensuelles": data.get("charges_mensuelles")
        })

        invalidate_user_intelligence_caches(email)
        
    return {"status": "updated"}


# alias sécurité (transition safe)
@router.put("/onboarding")
def onboarding_alias(data: dict, email: str = Depends(get_current_user)):
    return update_onboarding(data, email)
