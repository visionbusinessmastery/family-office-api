from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from database import engine
from auth.utils import hash_password, verify_password, create_token, get_current_user
from .schemas import UserProfileRequest

router = APIRouter()

# REGISTER
@router.post("/register")
def register(email: str, password: str):
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO users (email, password)
                VALUES (:email, :password)
            """), {
                "email": email,
                "password": hash_password(password)
            })
    except:
        raise HTTPException(status_code=400, detail="User exists")

    return {"status": "created"}


# LOGIN
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT email, password FROM users WHERE email=:email
        """), {"email": form_data.username}).fetchone()

    if not user or not verify_password(form_data.password, user[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({"sub": user[0]})
    return {"access_token": token, "token_type": "bearer"}


# ME
@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}


# SAVE PROFILE (ALIGNÉ AVEC TA DB ACTUELLE)
@router.post("/profile/save")
def save_profile(data: UserProfileRequest, user: str = Depends(get_current_user)):

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

    return {"status": "profil sauvegardé"}
