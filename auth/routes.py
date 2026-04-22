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

        # check if user exists
        existing = conn.execute(text("""
            SELECT id FROM users WHERE email = :email
        """), {"email": data.email}).fetchone()

        if existing:
            raise HTTPException(400, "User already exists")

        # create user
        result = conn.execute(text("""
            INSERT INTO users (email, is_verified, is_active)
            VALUES (:email, FALSE, FALSE)
            RETURNING id
        """), {
            "email": data.email
        })

        user_id = result.fetchone()[0]

    return {
        "message": "User created",
        "user_id": user_id
    }


# =========================
# VERIFY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(email: str):

    with engine.begin() as conn:

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
            SELECT password_hash FROM users WHERE email = :email
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
# LOGIN
# =========================
@router.post("/login")
def login(data: UserRegister):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT email, password_hash, is_verified
            FROM users
            WHERE email = :email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(401, "User not found")

        if not user.is_verified:
            raise HTTPException(403, "Email not verified")

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
    return {"email": user}
    

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
                investments,
                crypto,
                risk_profile
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
                0,0,0,0,'medium'
            )
            ON CONFLICT (user_email)
            DO UPDATE SET
                gender = EXCLUDED.gender,
                age = EXCLUDED.age,
                monthly_income = EXCLUDED.monthly_income
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "saved"}
