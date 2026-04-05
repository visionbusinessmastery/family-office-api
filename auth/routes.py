from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import text
from database import engine
from auth.utils import hash_password, verify_password, create_token, get_current_user
from jose import jwt, JWTError
from .schemas import UserProfileRequest
from passlib.context import CryptContext
import os

# ==================================================
# CONFIG AUTH
# ==================================================

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ==================================================
# REGISTER
# ==================================================
@router.post("/register")
def register(email: str, password: str):
    with engine.begin() as conn:
        try:
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

# ==================================================
# LOGIN
# ==================================================
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
    

# ==================================================
# GET ME
# ==================================================
@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}

# ==================================================
# SAVE PROFILE
# ==================================================
@router.post("/profile/save")
def save_profile(data: UserProfileRequest, user: str = Depends(get_current_user)):

    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO user_profiles (
            user_email, genre, age, situation_pro,
            revenus_mensuels, revenus_annuels,
            situation_familiale, enfants, nb_enfants,
            logement, valeur_bien, prix_achat,
            dettes, epargne, investissements
        )
        VALUES (
            :email, :genre, :age, :situation_pro,
            :revenus_mensuels, :revenus_annuels,
            :situation_familiale, :enfants, :nb_enfants,
            :logement, :valeur_bien, :prix_achat,
            :dettes, :epargne, :investissements
        )
        ON CONFLICT (user_email)
        DO UPDATE SET
            genre = EXCLUDED.genre,
            age = EXCLUDED.age,
            situation_pro = EXCLUDED.situation_pro,
            revenus_mensuels = EXCLUDED.revenus_mensuels,
            revenus_annuels = EXCLUDED.revenus_annuels,
            situation_familiale = EXCLUDED.situation_familiale,
            enfants = EXCLUDED.enfants,
            nb_enfants = EXCLUDED.nb_enfants,
            logement = EXCLUDED.logement,
            valeur_bien = EXCLUDED.valeur_bien,
            prix_achat = EXCLUDED.prix_achat,
            dettes = EXCLUDED.dettes,
            epargne = EXCLUDED.epargne,
            investissements = EXCLUDED.investissements,
            updated_at = CURRENT_TIMESTAMP
        """), {
            "email": user,
            **data.dict()
        })

    return {"status": "profil sauvegardé"}

