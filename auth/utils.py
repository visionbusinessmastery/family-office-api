# =========================
# IMPORTS
# =========================
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from sqlalchemy import text
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import os

# =========================
# CONFIG
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not SECRET_KEY:
    raise Exception("SECRET_KEY manquante")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()

# =========================
# HASH PASSWORD
# =========================
def hash_password(password: str):
    return pwd_context.hash(password)

# =========================
# VERIFY PASSWORD
# =========================
def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

# =========================
# CREATE TOKEN
# =========================
def create_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# DECODE TOKEN
# =========================
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Token invalide")

        return email

    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide")

# =========================
# GET CURRENT USER
# =========================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = credentials.credentials

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if not email:
            raise HTTPException(status_code=401, detail="Token invalide")

        return email

    except Exception as e:
        print("TOKEN ERROR:", e)
        raise HTTPException(status_code=401, detail="Token invalide")

# =========================
# BUILD UNLOCKS
# =========================
def build_unlocks(plan: str, level: str):

    base = ["dashboard"]

    if plan != "FREE":
        base.append("portfolio")

    if plan in ["GOLD", "ELITE"]:
        base.append("analytics")

    if level == "Advanced":
        base.append("ai_insights")

    if level == "Elite":
        base.append("family_office_ai")

    return base


# =========================
# GET USER ID
# =========================
def get_user_id(conn, email: str):

    row = conn.execute(
        text("""
            SELECT id
            FROM users
            WHERE email = :email
        """),
        {"email": email}
    ).fetchone()

    return row.id if row else None
