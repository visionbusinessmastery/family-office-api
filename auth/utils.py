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
import logging

from product.entitlements import normalize_plan, plan_allows


logger = logging.getLogger(__name__)

# =========================
# CONFIG
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

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
        logger.warning("Token error: %s", e)
        raise HTTPException(status_code=401, detail="Token invalide")

# =========================
# BUILD UNLOCKS
# =========================
def build_unlocks(plan: str, level: str):

    base = ["dashboard"]
    normalized_plan = normalize_plan(plan)
    normalized_level = (level or "").upper()

    base.append("portfolio")

    if plan_allows(normalized_plan, "GOLD"):
        base.append("analytics")

    if normalized_level in ["ADVANCED", "ELITE", "ELITE INVESTOR", "FAMILY OFFICE OPERATOR", "LIBERTY", "LEGACY", "DYNASTY ARCHITECT"]:
        base.append("guided_insights")

    if normalized_level in ["ELITE", "ELITE INVESTOR", "FAMILY OFFICE OPERATOR", "LIBERTY", "LEGACY", "DYNASTY ARCHITECT"]:
        base.append("family_office_guidance")

    if plan_allows(normalized_plan, "LEGACY"):
        base.extend(["family_vault", "heirs_mode", "dynasty_office"])

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
