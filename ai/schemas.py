from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# ==================================================
# MODELS
# ==================================================

class BrainRequest(BaseModel):
    question: str

