from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict
from database import Base
from sqlalchemy import Column, Integer, String, Float

# ==================================================
# MODELS
# ==================================================

class BrainRequest(BaseModel):
    question: str

