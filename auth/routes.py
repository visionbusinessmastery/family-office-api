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

    hashed_password = hash_password(data.password)

    with engine.begin() as conn:

        # create user
        result = conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified)
            VALUES (:email, :password_hash, FALSE)
            RETURNING id
        """), {
            "email": data.email,
            "password_hash": hashed_password
        })

        user_id = result.fetchone()[0]

        # verification token
        token = secrets.token_urlsafe(32)

        conn.execute(text("""
            INSERT INTO email_verifications (user_id, email, token, is_used, expires_at)
            VALUES (:user_id, :email, :token, FALSE, NOW() + INTERVAL '24 hours')
        """), {
            "user_id": user_id,
            "email": data.email,
            "token": token
        })

    return {
        "message": "User created",
        "user_id": user_id
    }


# =========================
# LOGIN
# =========================
@router.post("/login")
def login(data: UserLogin):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(401, "User not found")

        if not verify_password(data.password, user.password_hash):
            raise HTTPException(401, "Wrong password")

        if not user.is_verified:
            raise HTTPException(403, "Email not verified")

    return {
        "access_token": create_token({"sub": data.email}),
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

    return {"status": "verified"}


# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT * FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        hashed = hash_password(data.password)

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password
            WHERE email = :email
        """), {
            "email": data.email,
            "password": hashed
        })

    return {"status": "password set"}
