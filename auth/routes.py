from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from datetime import datetime
import secrets

from database import engine

from auth.schemas import (
    UserRegister,
    UserLogin,
    UserProfileRequest,
    SetPasswordRequest
)

from auth.utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user
)

router = APIRouter()

# =========================
# REGISTER
# =========================
@router.post("/register")
def register(data: UserRegister):

    with engine.begin() as conn:

        # 1. create user
        result = conn.execute(text("""
            INSERT INTO users (email, is_verified, is_active)
            VALUES (:email, FALSE, FALSE)
            RETURNING id
        """), {
            "email": data.email
        })

        user_id = result.fetchone()[0]

        # 2. generate token
        token = generate_verification_token()

        # 3. save verification
        save_verification_token(data.email, token)

    return {
        "message": "User created",
        "user_id": user_id,
        "next_step": "verify-email"
    }

# =========================
# LOGIN
# =========================
@router.post("/login")
def login(data: UserRegister):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(401, "User not found")

        if not user.is_verified:
            raise HTTPException(403, "Email not verified")

        if not user.password_hash:
            raise HTTPException(403, "Password not set")

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "Wrong password")

        token = create_token({"sub": user.email})

        return {
            "access_token": token,
            "token_type": "bearer"
        }

# =========================
# ME
# =========================
@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}


# =========================
# PROFILE SAVE
# =========================
@router.post("/profile/save")
def save_profile(
    data: UserProfileRequest,
    user: str = Depends(get_current_user)
):

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO user_profiles (
                user_email, gender, age, employment_status,
                monthly_income, marital_status, children_count,
                housing_status, real_estate_value, real_estate_purchase_price,
                total_debt, savings, investments, crypto, risk_profile
            )
            VALUES (
                :email, :genre, :age, :situation_pro,
                :revenus_mensuels, :situation_familiale, :nb_enfants,
                :logement, :valeur_bien, :prix_achat,
                :dettes, :epargne, :investissements, 0, 'medium'
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
                real_estate_purchase_price = EXCLUDED.real_estate_purchase_price
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "profile saved"}


# =========================
# VERIFY EMAIL
# =========================@router.get("/verify-email")
def verify_email(token: str):

    with engine.begin() as conn:

        record = conn.execute(text("""
            SELECT user_id, email, expires_at, is_used
            FROM email_verifications
            WHERE token = :token
        """), {"token": token}).fetchone()

        if not record:
            raise HTTPException(400, "Invalid token")

        user_id, email, expires_at, is_used = record

        if is_used:
            return {"status": "already_used"}

        if expires_at < datetime.utcnow():
            raise HTTPException(400, "Token expired")

        # mark used
        conn.execute(text("""
            UPDATE email_verifications
            SET is_used = TRUE
            WHERE token = :token
        """), {"token": token})

        # activate user
        conn.execute(text("""
            UPDATE users
            SET is_verified = TRUE
            WHERE id = :user_id
        """), {"user_id": user_id})

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
            SELECT id, password_hash FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        if user.password_hash:
            raise HTTPException(400, "Password already set")

        hashed = hash_password(data.password)

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password,
                is_active = TRUE
            WHERE email = :email
        """), {
            "email": data.email,
            "password": hashed
        })

    return {"status": "password set"}



# =========================
# PROFILE SAVED
# =========================
@router.post("/profile/save")
def save_profile(
    data: UserProfileRequest,
    user: str = Depends(get_current_user)
):

    with engine.begin() as conn:

        conn.execute(text("""
            INSERT INTO user_profiles (
                user_email, gender, age, employment_status,
                monthly_income, marital_status, children_count,
                housing_status, real_estate_value, real_estate_purchase_price,
                total_debt, savings, investments, crypto, risk_profile
            )
            VALUES (
                :email, :genre, :age, :situation_pro,
                :revenus_mensuels, :situation_familiale, :nb_enfants,
                :logement, :valeur_bien, :prix_achat,
                0, 0, 0, 0, 'medium'
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                employment_status = EXCLUDED.employment_status,
                monthly_income = EXCLUDED.monthly_income
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "profile saved"}
