from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from datetime import datetime, timedelta
import secrets

from database import engine
from auth.utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user
)

from auth.schemas import (
    UserAuth,
    UserProfileRequest,
    SetPasswordRequest
)

import stripe
import os
from fastapi import Request


router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# =========================
# REGISTER
# =========================
@router.post("/register")
def register(data: UserAuth):

    with engine.begin() as conn:

        existing = conn.execute(text("""
            SELECT id FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if existing:
            raise HTTPException(400, "User already exists")

        hashed_password = hash_password(data.password)

        result = conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified)
            VALUES (:email, :password_hash, FALSE)
            RETURNING id
        """), {
            "email": data.email,
            "password_hash": hashed_password
        })

        user_id = result.fetchone()[0]

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        conn.execute(text("""
            INSERT INTO email_verifications (user_id, email, token, expires_at, is_used)
            VALUES (:user_id, :email, :token, :expires_at, FALSE)
        """), {
            "user_id": user_id,
            "email": data.email,
            "token": token,
            "expires_at": expires_at
        })

    return {
        "message": "User created",
        "user_id": user_id,
        "verification_token": token
    }


# =========================
# LOGIN
# =========================
@router.post("/login")
def login(data: UserAuth):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT id, email, password_hash, is_verified, profile_completed, plan
            FROM users
            WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(401, "User not found")

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "Wrong password")

        if not user.is_verified:
            raise HTTPException(403, "Email not verified")

        token = create_token({"sub": user.email})

        return {
            "access_token": token,
            "token_type": "bearer",
            "profile_completed": user.profile_completed,
            "plan": user.plan
        }


# =========================
# ME
# =========================
@router.get("/me")
def me(user: str = Depends(get_current_user)):

    with engine.begin() as conn:

        result = conn.execute(text("""
            SELECT email, profile_completed, plan
            FROM users
            WHERE email = :email
        """), {"email": user}).fetchone()

        if not result:
            raise HTTPException(404, "User not found")

        email, profile_completed, plan = result

    return {
        "email": email,
        "profile_completed": profile_completed,
        "plan": plan
    }

# =========================
# PROFILE SAVE (LIGHT)
# =========================
@router.post("/profile/save")
def save_profile(
    data: UserProfileRequest,
    user: str = Depends(get_current_user)
):

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO user_profiles (
                user_email,
                gender,
                age,
                employment_status
            )
            VALUES (
                :email,
                :genre,
                :age,
                :situation_pro
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                employment_status = EXCLUDED.employment_status,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            "genre": data.genre,
            "age": data.age,
            "situation_pro": data.situation_pro,
        })

    return {"status": "profile saved"}


# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(token: str):

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

    return {
        "status": "verified",
        "email": email
    }


# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT password_hash FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        if user.password_hash:
            raise HTTPException(400, "Password already set")

        hashed = hash_password(data.password)

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password
            WHERE email = :email
        """), {
            "email": data.email,
            "password": hashed
        })

    token = create_token({"sub": data.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# =========================
# ONBOARDING PROFILE SAVE (MAIN)
# =========================
@router.post("/onboarding/save")
def onboarding_save(
    data: UserProfileRequest,
    user: str = Depends(get_current_user)
):

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO user_profiles (
                user_email,
                gender,
                age,
                employment_status,
                monthly_income,
                marital_status,
                children_count,
                housing_status,
                real_estate_value,
                real_estate_purchase_price,
                total_debt,
                savings,
                investments
            )
            VALUES (
                :email,
                :genre,
                :age,
                :situation_pro,
                :revenus_mensuels,
                :situation_familiale,
                :nb_enfants,
                :logement,
                :valeur_bien,
                :prix_achat,
                :dettes,
                :epargne,
                :investissements
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                employment_status = EXCLUDED.employment_status,
                monthly_income = EXCLUDED.monthly_income,
                marital_status = EXCLUDED.marital_status,
                children_count = EXCLUDED.children_count,
                housing_status = EXCLUDED.housing_status,
                real_estate_value = EXCLUDED.real_estate_value,
                real_estate_purchase_price = EXCLUDED.real_estate_purchase_price,
                total_debt = EXCLUDED.total_debt,
                savings = EXCLUDED.savings,
                investments = EXCLUDED.investments,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            **data.dict()
        })

        conn.execute(text("""
            UPDATE users
            SET profile_completed = TRUE
            WHERE email = :email
        """), {"email": user})

    return {
        "status": "onboarding completed",
        "profile_completed": True
    }


# =========================
# UPDATE PLAN
# =========================
@router.post("/plan/update")
def update_plan(
    plan: str,
    user: str = Depends(get_current_user)
):

    allowed_plans = ["FREE", "SILVER", "GOLD", "ELITE"]

    if plan not in allowed_plans:
        raise HTTPException(400, "Invalid plan")

    with engine.begin() as conn:

        conn.execute(text("""
            UPDATE users
            SET plan = :plan
            WHERE email = :email
        """), {
            "plan": plan,
            "email": user
        })

    return {
        "status": "plan updated",
        "plan": plan
    }


# =========================
# CREATE STRIPE CHECKOUT SESSION
# =========================
@router.post("/billing/create-checkout-session")
def create_checkout_session(
    plan: str,
    user: str = Depends(get_current_user)
):

    price_mapping = {
        "SILVER": "price_silver_prod_UNyBukgn7HCdYL",
        "GOLD": "price_gold_prod_UNyF2ShyswcDzY",
        "ELITE": "price_elite_prod_UNyGSrDkrgyjec"
    }

    if plan not in price_mapping:
        raise HTTPException(400, "Invalid plan")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",

            # 👇 email utilisateur
            customer_email=user,

            line_items=[
                {
                    "price": price_mapping[plan],
                    "quantity": 1,
                }
            ],

            # ✅ dynamique (important prod)
            success_url=f"{FRONTEND_URL}/dashboard?success=true",
            cancel_url=f"{FRONTEND_URL}/dashboard?canceled=true",

            # 🔥 CRUCIAL POUR WEBHOOK
            metadata={
                "user_email": user,
                "plan": plan
            }
        )

        return {"url": session.url}

    except Exception as e:
        raise HTTPException(500, str(e))


import stripe
from fastapi import Request

# =========================
# STRIPE WEBHOOK
# =========================
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            endpoint_secret
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # =========================
    # PAYMENT SUCCESS
    # =========================
    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]

        customer_email = session.get("customer_email")
        plan = session.get("metadata", {}).get("plan")

        if customer_email and plan:

            with engine.begin() as conn:

                # 1. UPDATE PLAN USER
                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan,
                        subscription_status = 'active'
                    WHERE email = :email
                """), {
                    "plan": plan,
                    "email": customer_email
                })

    return {"status": "success"}
