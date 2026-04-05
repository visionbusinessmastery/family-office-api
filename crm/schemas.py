from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# ==================================================
# MODELS
# ==================================================

class LeadRequest(BaseModel):
    name: str
    email: str
