from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict
from database import Base
from sqlalchemy import Column, Integer, String, Float

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
