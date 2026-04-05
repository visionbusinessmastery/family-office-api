from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# ==================================================
# MODELS
# ==================================================

class LeadRequest(BaseModel):
    name: str
    email: str

class UserProfile(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
