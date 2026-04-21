from core.limiter import limiter
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from datetime import datetime

from database import engine

from auth.utils import (
    hash_password,
    verify_password,
    create_token,
    get_current_user
)

from .schemas import UserRegister, UserProfileRequest, SetPasswordRequest

from auth.email_service import send_verification_email
from auth.verification import generate_verification_token, save_verification_token


router = APIRouter()


# =========================
# REGISTER
# =========================
@router.post("/register")
@limiter.limit("2/minute")
def register(request: Request, data: UserRegister):

    with engine.begin() as conn:

        existing = conn.execute(text("""
            SELECT email FROM users WHERE email=:email
        """), {"email": data.email}).fetchone()

        if existing:
            raise HTTPException(400, "email déjà utilisé")

        # ⚠️ password_hash UNIQUEMENT (standard SaaS)
        conn.execute(text("""
            INSERT INTO users (email, password_hash, is_verified)
            VALUES (:email, :password, FALSE)
        """), {
            "email": data.email,
            "password": hash_password(data.password)
        })

        token = generate_verification_token()
        save_verification_token(data.email, token)
        send_verification_email(data.email, token)

    return {"status": "created"}


# =========================
# LOGIN (OAUTH Swagger COMPATIBLE)
# =========================
@router.post("/login")
@limiter.limit("3/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):

    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT email, password_hash FROM users WHERE email=:email
        """), {"email": form_data.username}).fetchone()
      
    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": user[0]})

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
# SAVE PROFILE (FIX CLEAN)
# =========================
@router.post("/profile/save")
def save_profile(
    request: Request,
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
            monthly_income = EXCLUDED.monthly_income,
            marital_status = EXCLUDED.marital_status,
            children_count = EXCLUDED.children_count,
            housing_status = EXCLUDED.housing_status,
            real_estate_value = EXCLUDED.real_estate_value,
            real_estate_purchase_price = EXCLUDED.real_estate_purchase_price,
            updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            **data.dict()
        })
        

# =========================
# VERFIY EMAIL
# =========================
@router.get("/verify-email")
def verify_email(token: str):

    with engine.begin() as conn:

        record = conn.execute(text("""
            SELECT email, expires_at, verified
            FROM email_verifications
            WHERE token = :token
        """), {"token": token}).fetchone()

        if not record:
            raise HTTPException(400, "Invalid token")

        email, expires_at, verified = record

        if verified:
            return {"status": "already_verified"}

        if expires_at < datetime.utcnow():
            raise HTTPException(400, "Token expired")

        # mark verified
        conn.execute(text("""
            UPDATE email_verifications
            SET verified = TRUE
            WHERE token = :token
        """), {"token": token})

        # 🧠 create user si pas existant (PENDING PASSWORD)
        conn.execute(text("""
            INSERT INTO users (email, is_verified)
            VALUES (:email, TRUE)
            ON CONFLICT (email) DO UPDATE SET is_verified = TRUE
        """), {"email": email})

    return {
        "status": "verified",
        "email": email,
        "next_step": "/create-password"
    }
    

# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    with engine.begin() as conn:

        user = conn.execute(text("""
            SELECT email, password_hash
            FROM users
            WHERE email=:email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(404, "User not found")

        if user[1]:
            raise HTTPException(400, "Password already set")

        hashed = hash_password(data.password)

        conn.execute(text("""
            UPDATE users
            SET password_hash = :password,
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
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
