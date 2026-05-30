# =========================
# IMPORTS
# =========================
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request
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
from core.cache import delete_cache_keys, delete_cache_patterns
from core.limiter import limiter
from product.entitlements import normalize_plan, resolve_effective_plan
from privacy.routes import record_consents
from security.abuse_engine import assert_ip_rate_limit
from security.audit import ensure_security_tables, log_security_event
from analytics.analytics_events import ONBOARDING_COMPLETED
from analytics.posthog_service import capture_event

router = APIRouter()

# =========================
# INVALIDATE USER
# =========================
def invalidate_user_intelligence_caches(email: str):
    delete_cache_keys(f"score:{email}")
    delete_cache_patterns(
        f"intel:{email}*",
        f"context:{email}*",
        f"gamification:{email}*",
        f"quests:{email}*",
    )



# =========================
# REGISTER
# =========================
@router.post("/register")
@limiter.limit("3/hour")
def register(data: UserAuth, request: Request):

    email = data.email.lower()
    consents = data.model_dump(exclude={"email"}, exclude_none=True)

    try:
        with engine.begin() as conn:
            ensure_security_tables(conn)
            assert_ip_rate_limit(conn, "auth_register", 3, "hour", request)

            existing = conn.execute(text("""
                SELECT id, is_verified FROM users WHERE email = :email
            """), {"email": email}).fetchone()

            if existing:

                if existing.is_verified:
                    log_security_event(conn, "register_existing_verified", request, email=email)
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
                log_security_event(conn, "register_verification_resent", request, email=email)

                return {"status": "success", "action": "resend_verification"}

            if not data.terms_accepted or not data.privacy_policy_accepted:
                raise HTTPException(
                    status_code=400,
                    detail="Les CGU et la politique de confidentialite doivent etre acceptees pour creer un compte.",
                )

            result = conn.execute(text("""
                INSERT INTO users (email, is_verified, verification_attempts, profile_completed)
                VALUES (:email, FALSE, 0, FALSE)
                RETURNING id
            """), {"email": email})

            user_id = result.fetchone()[0]
            record_consents(conn, user_id, consents, request)
            log_security_event(conn, "register_created", request, email=email, user_id=user_id)

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
@limiter.limit("10/hour")
def verify_email(request: Request, token: str):

    with engine.begin() as conn:
        ensure_security_tables(conn)
        assert_ip_rate_limit(conn, "auth_verify_email", 10, "hour", request)

        record = conn.execute(text("""
            SELECT email FROM email_verifications
            WHERE token = :token
            AND is_used = FALSE
            AND expires_at > NOW()
        """), {"token": token}).fetchone()

        if not record:
            log_security_event(conn, "verify_email_failed", request, severity="warning")
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
        log_security_event(conn, "verify_email_success", request, email=email)

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
            SELECT
                users.email,
                users.plan AS user_plan,
                users.profile_completed,
                users.age,
                users.situation_pro,
                users.revenus_mensuels,
                users.charges_mensuelles,
                users.is_founder,
                users.founder_tier,
                users.founder_discount,
                subscriptions.plan AS subscription_plan,
                subscriptions.status AS subscription_status
            FROM users
            LEFT JOIN subscriptions ON subscriptions.user_id = users.id
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
            "plan": resolve_effective_plan(
                user.user_plan,
                user.subscription_plan,
                user.subscription_status,
            ),
            "profile_completed": profile_completed,
            "age": user.age,
            "situation_pro": user.situation_pro,
            "revenus_mensuels": user.revenus_mensuels or 0,
            "charges_mensuelles": user.charges_mensuelles or 0,
            "is_founder": bool(user.is_founder),
            "founder_tier": user.founder_tier,
            "founder_discount": int(user.founder_discount or 0),
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
@limiter.limit("5/minute")
def login(data: LoginRequest, request: Request):

    email = data.email.lower()

    with engine.begin() as conn:
        ensure_security_tables(conn)
        assert_ip_rate_limit(conn, "auth_login", 5, "minute", request)

        user = conn.execute(text("""
            SELECT password_hash FROM users WHERE email = :email
        """), {"email": email}).fetchone()

        if not user:
            log_security_event(conn, "login_failed", request, email=email, severity="warning")
            raise HTTPException(status_code=400, detail="Identifiants incorrects")

        if user.password_hash is None:
            log_security_event(conn, "login_set_password_required", request, email=email)
            return {"action": "set_password_required"}

        if not verify_password(data.password, user.password_hash):
            log_security_event(conn, "login_failed", request, email=email, severity="warning")
            raise HTTPException(status_code=400, detail="Identifiants incorrects")

    token = create_token({"sub": email})
    with engine.begin() as conn:
        log_security_event(conn, "login_success", request, email=email)

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
    normalized_plan = normalize_plan(plan)

    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users SET plan = :plan WHERE email = :email
        """), {"plan": normalized_plan, "email": email})

        invalidate_user_intelligence_caches(email)
        user_id = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).scalar()
        capture_event(conn, ONBOARDING_COMPLETED, user_id=user_id, email=email)

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
        user_id = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": email}).scalar()
        capture_event(conn, ONBOARDING_COMPLETED, user_id=user_id, email=email)
        
    return {"status": "completed"}


# =========================
# UPDATE ONBOARDING (CLEAN FINAL VERSION)
# =========================
@router.put("/onboarding/update")
def update_onboarding(data: dict, email: str = Depends(get_current_user)):

    with engine.begin() as conn:

        conn.execute(text("""
            UPDATE users
            SET age = COALESCE(:age, age),
                situation_pro = COALESCE(:situation_pro, situation_pro),
                revenus_mensuels = COALESCE(:revenus_mensuels, revenus_mensuels),
                charges_mensuelles = COALESCE(:charges_mensuelles, charges_mensuelles)
            WHERE email = :email
        """), {
            "email": email,
            "age": data.get("age"),
            "situation_pro": data.get("situation_pro"),
            "revenus_mensuels": data.get("revenus_mensuels"),
            "charges_mensuelles": data.get("charges_mensuelles")
        })

        invalidate_user_intelligence_caches(email)
        
    return {"status": "updated"}


# alias sécurité (transition safe)
@router.put("/onboarding")
def onboarding_alias(data: dict, email: str = Depends(get_current_user)):
    return update_onboarding(data, email)
