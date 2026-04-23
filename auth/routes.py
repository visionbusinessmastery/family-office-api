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
    build_unlocks   # ✅ AJOUT
)

from auth.schemas import (
    UserAuth,
    UserProfileRequest,
    SetPasswordRequest
)

from intelligence.analyzers.family_office_score import compute_family_office_score

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# 🔒 SECURITÉ API KEY STRIPE
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

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        conn.execute(text("""
            INSERT INTO email_verifications (user_id, email, token, expires_at, is_used)
            VALUES (:user_id, :email, :token, :expires_at, FALSE)
        """), {
            "user_id": user_id,
            "email": email,
            "token": token,
            "expires_at": expires_at
        })

    return {
        "message": "User created",
        "user_id": user_id,
        "verification_required": True
    }
    

# =========================
# LOGIN
# =========================
@router.post("/login")
def login(data: UserAuth):

    email = data.email.lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT id, email, password_hash, is_verified, profile_completed, plan
            FROM users
            WHERE email = :email
        """), {"email": email}).fetchone()

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
            SELECT *
            FROM users
            WHERE email = :email
        """), {"email": user}).fetchone()

        profile = conn.execute(text("""
            SELECT *
            FROM user_profiles
            WHERE user_email = :email
        """), {"email": user}).fetchone()

        portfolio = conn.execute(text("""
            SELECT *
            FROM portfolio
            WHERE user_email = :email
        """), {"email": user}).fetchall()

    # -------------------------
    # SCORE ENGINE
    # -------------------------
    score_data = compute_family_office_score(
        dict(profile._mapping) if profile else {},
        [dict(p._mapping) for p in portfolio] if portfolio else []
    )

    return {
        "email": result.email,
        "plan": result.plan,
        "profile_completed": result.profile_completed,
        "profile_stage": profile.profile_stage if profile else "basic",

        "family_office_score": score_data["score"],
        "level": score_data["level"],
        "advice": score_data["advice"],

        "unlock_features": build_unlocks(result.plan, score_data["level"])
    }

# =========================
# PROFILE SAVE (LIGHT)
# =========================
@router.post("/profile/save")
def save_profile(data: UserProfileRequest, user: str = Depends(get_current_user)):

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


# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    email = data.email.lower()

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT password_hash FROM users WHERE email = :email
        """), {"email": email}).fetchone()

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
            "email": email,
            "password": hashed
        })

    token = create_token({"sub": email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }


# =========================
# ONBOARDING / PROFILE UPDATE (PROGRESSIVE)
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
                :gender,
                :age,
                :employment_status,
                :monthly_income,
                :marital_status,
                :children_count,
                :housing_status,
                :real_estate_value,
                :real_estate_purchase_price,
                :total_debt,
                :savings,
                :investments
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender = COALESCE(EXCLUDED.gender, user_profiles.gender),
                age = COALESCE(EXCLUDED.age, user_profiles.age),
                employment_status = COALESCE(EXCLUDED.employment_status, user_profiles.employment_status),
                monthly_income = COALESCE(EXCLUDED.monthly_income, user_profiles.monthly_income),
                marital_status = COALESCE(EXCLUDED.marital_status, user_profiles.marital_status),
                children_count = COALESCE(EXCLUDED.children_count, user_profiles.children_count),
                housing_status = COALESCE(EXCLUDED.housing_status, user_profiles.housing_status),
                real_estate_value = COALESCE(EXCLUDED.real_estate_value, user_profiles.real_estate_value),
                real_estate_purchase_price = COALESCE(EXCLUDED.real_estate_purchase_price, user_profiles.real_estate_purchase_price),
                total_debt = COALESCE(EXCLUDED.total_debt, user_profiles.total_debt),
                savings = COALESCE(EXCLUDED.savings, user_profiles.savings),
                investments = COALESCE(EXCLUDED.investments, user_profiles.investments),
                updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            "gender": data.gender,
            "age": data.age,
            "employment_status": data.situation_pro,

            "monthly_income": data.monthly_income,
            "marital_status": data.marital_status,
            "children_count": data.children_count,
            "housing_status": data.housing_status,
            "real_estate_value": data.real_estate_value,
            "real_estate_purchase_price": data.real_estate_purchase_price,
            "total_debt": data.total_debt,
            "savings": data.savings,
            "investments": data.investments
        })

        # On peut garder ça MAIS ce n’est plus un onboarding strict
        conn.execute(text("""
            UPDATE users
            SET profile_completed = TRUE
            WHERE email = :email
        """), {"email": user})

    return {
        "status": "profile updated",
        "profile_completed": True
    }


# =========================
# UPDATE PLAN
# =========================
@router.post("/plan/update")
def update_plan(plan: str, user: str = Depends(get_current_user)):

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

    return {"status": "plan updated", "plan": plan}


# =========================
# STRIPE CHECKOUT
# =========================
@router.post("/billing/create-checkout-session")
def create_checkout_session(plan: str, user: str = Depends(get_current_user)):

    price_mapping = {
        "SILVER": "price_1TPCFFPdcZID0JqGbGk1LJoC",
        "GOLD": "price_1TPCIdPdcZID0JqG2T0jFKGU",
        "ELITE": "price_1TPCJpPdcZID0JqGG23BGZdtc"
    }

    if plan not in price_mapping:
        raise HTTPException(400, "Invalid plan")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=user,

        line_items=[
            {
                "price": price_mapping[plan],
                "quantity": 1,
            }
        ],

        allow_promotion_codes=True,

        success_url=f"{FRONTEND_URL}/dashboard?success=true",
        cancel_url=f"{FRONTEND_URL}/dashboard?canceled=true",

        metadata={
            "user_email": user,
            "plan": plan
        }
    )

    return {"url": session.url}


# =========================
# STRIPE WEBHOOK
# =========================
@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(400, "Missing stripe-signature header")

    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not endpoint_secret:
        raise HTTPException(500, "Missing STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        raise HTTPException(400, str(e))

    print("STRIPE EVENT:", event["type"])

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored"}

    session = event["data"]["object"]

    customer_email = session.get("customer_email") or session.get("customer_details", {}).get("email")
    plan = session.get("metadata", {}).get("plan")

    print("EMAIL:", customer_email)
    print("PLAN:", plan)

    if customer_email and plan:

        with engine.begin() as conn:

            conn.execute(text("""
                UPDATE users
                SET plan = :plan,
                    subscription_status = 'active'
                WHERE email = :email
                AND subscription_status != 'active'
            """), {
                "plan": plan,
                "email": customer_email
            })

    return {"status": "success"}
