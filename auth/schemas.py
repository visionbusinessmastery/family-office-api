from pydantic import BaseModel, EmailStr
from typing import Optional


# =========================
# REGISTER / LOGIN
# =========================
class UserAuth(BaseModel):
    email: EmailStr
    terms_accepted: Optional[bool] = None
    privacy_policy_accepted: Optional[bool] = None
    ai_processing_accepted: Optional[bool] = None
    marketing_emails_accepted: Optional[bool] = None
    analytics_accepted: Optional[bool] = None
    personalized_opportunities_accepted: Optional[bool] = None
    weekly_reports_accepted: Optional[bool] = None
    third_party_data_processing_accepted: Optional[bool] = None


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
