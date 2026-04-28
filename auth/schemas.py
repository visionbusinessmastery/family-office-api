from pydantic import BaseModel, EmailStr
from typing import Optional


# =========================
# REGISTER / LOGIN
# =========================
class UserAuth(BaseModel):
    email: EmailStr


# =========================
# PROFILE
# =========================
class UserProfileRequest(BaseModel):
    genre: Optional[str] = None
    age: Optional[int] = None
    situation_pro: Optional[str] = None


# =========================
# SET PASSWORD (step après vérification)
# =========================
class SetPasswordRequest(BaseModel):
    email: EmailStr
    password: str


# =========================
# LOGIN REQUEST
# =========================
class LoginRequest(BaseModel):
    email: str
    password: str
