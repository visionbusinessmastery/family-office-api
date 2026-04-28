import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text

from database import engine
from auth.schemas import UserAuth, SetPasswordRequest
from auth.utils import hash_password, create_token, get_current_user, verify_password
from auth.email_service import send_verification_email

from passlib.context import CryptContext

router = APIRouter()


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
                        "action": "login",
                        "message": "Compte existant"
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

                return {
                    "status": "success",
                    "action": "resend_verification"
                }

            # ✅ CREATE USER WITHOUT PASSWORD (OK)
            result = conn.execute(text("""
                INSERT INTO users (email, is_verified, verification_attempts)
                VALUES (:email, FALSE, 0)
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

        # EMAIL SAFE
        try:
            send_verification_email(email, token)
        except Exception as e:
            print("EMAIL ERROR:", e)

        return {
            "status": "success",
            "action": "verify_email",
            "user_id": user_id
        }

    except Exception as e:
        print("REGISTER ERROR FULL:", repr(e))
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
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE token = :token
        """), {"token": token})

        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE
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

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password
            WHERE email = :email
            AND is_verified = TRUE
        """), {"email": email, "password": password_hash})

        if conn.rowcount == 0:
            raise HTTPException(
                status_code=400,
                detail="Email non vérifié"
            )

    token = create_token({"sub": email})

    return {"access_token": token}


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
# LOGIN
# =========================
@router.post("/login")
def login(data: SetPasswordRequest):

    email = data.email.lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT password_hash FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Utilisateur introuvable")

        if not user.password_hash:
            raise HTTPException(
                status_code=400,
                detail="Mot de passe non défini. Vérifie ton email."
            )
    
        if not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Mot de passe incorrect")

    token = create_token({"sub": email})

    return {"access_token": token}


# =========================
# ONBOARDING
# =========================
@router.post("/onboarding/save")
def save_onboarding(data: dict, email: str = get_current_user):

    try:
        with engine.begin() as conn:

            conn.execute(text("""
                UPDATE users
                SET
                    profile_completed = TRUE,
                    genre = :genre,
                    age = :age,
                    situation_pro = :situation_pro,
                    revenus_mensuels = :revenus,
                    dettes = :dettes,
                    epargne = :epargne
                WHERE email = :email
            """), {
                "email": email,
                "genre": data.get("genre"),
                "age": data.get("age"),
                "situation_pro": data.get("situation_pro"),
                "revenus": data.get("revenus_mensuels", 0),
                "dettes": data.get("dettes", 0),
                "epargne": data.get("epargne", 0),
            })

        return {"status": "ok"}

    except Exception as e:
        print("ONBOARDING ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Erreur onboarding")


# =========================
# PLAN UPDATE (MANUEL)
# =========================
@router.post("/plan/update")
def update_plan(plan: str, email: str = get_current_user):

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users SET plan = :plan WHERE email = :email
        """), {"plan": plan, "email": email})

    return {"status": "updated"}
