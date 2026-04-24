from pydantic import BaseModel, Field, EmailStr
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
# SET PASSWORD
# =========================
class SetPasswordRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
