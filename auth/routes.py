from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import text
from database import engine
from auth.utils import hash_password, verify_password, create_token
from jose import jwt, JWTError
import os

router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except:
        raise HTTPException(status_code=401, detail="Token invalide")

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

@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}
