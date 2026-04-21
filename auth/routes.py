from core.limiter import limiter
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from database import engine

from auth.utils import hash_password, verify_password, create_token, get_current_user
from .schemas import UserRegister, UserProfileRequest, SetPasswordRequest

from auth.email_service import send_verification_email
from auth.verification import generate_verification_token, save_verification_token

from auth.verification import verify_email_token

router = APIRouter()


# =========================
# REGISTER
# =========================
@router.post("/register")
@limiter.limit("2/minute")
def register(request: Request, data: UserRegister):

    try:
        with engine.begin() as conn:

            # 🔥 CHECK SI EMAIL EXISTE (AJOUT)
            existing_user = conn.execute(text("""
                SELECT email FROM users WHERE email=:email
            """), {"email": data.email}).fetchone()

            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="email déjà utilisé"
                )

            # 🔥 INSERT SI OK
            conn.execute(text("""
                INSERT INTO users (email, password)
                VALUES (:email, :password)
            """), {
                "email": data.email,
                "password": hash_password(data.password)
            })
            
            # ⭐ AJOUT IMPORTANT
            token = generate_verification_token()
            save_verification_token(data.email, token)
            send_verification_email(data.email, token)

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="erreur lors de la création du compte"
        )

    return {"status": "created"}


# =========================
# LOGIN (OAUTH Swagger COMPATIBLE)
# =========================
@router.post("/login")
@limiter.limit("3/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):

    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT email, password FROM users WHERE email=:email
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
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from datetime import datetime
from database import engine

router = APIRouter()


@router.get("/verify-email")
def verify_email(token: str):

    with engine.begin() as conn:

        # 1. récupérer email verification
        record = conn.execute(text("""
            SELECT email, expires_at, verified
            FROM email_verifications
            WHERE token = :token
        """), {"token": token}).fetchone()

        if not record:
            raise HTTPException(status_code=400, detail="Invalid token")

        email = record[0]
        expires_at = record[1]
        already_verified = record[2]

        # 2. déjà utilisé
        if already_verified:
            return {"status": "already_verified", "email": email}

        # 3. expiration check
        if expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Token expired")

        # 4. mark email as verified
        conn.execute(text("""
            UPDATE email_verifications
            SET verified = TRUE
            WHERE token = :token
        """), {"token": token})

        # 5. 🟢 CRÉATION USER AUTOMATIQUE (PENDING PASSWORD)
        conn.execute(text("""
            INSERT INTO users (email, is_verified, password, created_at)
            VALUES (:email, TRUE, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT (email)
            DO UPDATE SET is_verified = TRUE
        """), {"email": email})

    # 6. response clean SaaS
    return {
        "status": "verified",
        "email": email,
        "next_step": "create_password"
    }
    

# =========================
# SET PASSWORD
# =========================
@router.post("/set-password")
def set_password(data: SetPasswordRequest):

    with engine.begin() as conn:

        # 1. Vérifier si user existe
        user = conn.execute(text("""
            SELECT email, password FROM users WHERE email=:email
        """), {"email": data.email}).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # 2. Anti double setup password
        if user[1] is not None:
            raise HTTPException(status_code=400, detail="Password already set")

        # 3. Hash password
        hashed = hash_password(data.password)

        # 4. Update user
        conn.execute(text("""
            UPDATE users
            SET password = :password,
                is_active = true,
                is_verified = true,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = :email
        """), {
            "email": data.email,
            "password": hashed
        })

    # 5. AUTO LOGIN TOKEN (SAAS FLOW)
    token = create_token({"sub": data.email})

    return {
        "access_token": token,
        "token_type": "bearer"
    }
