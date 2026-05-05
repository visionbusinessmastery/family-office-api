# =========================
# IMPORTS
# =========================
from pydantic import BaseModel, Field
from typing import Optional


# =========================
# GLOBAL INTELLIGENCE REQUEST
# =========================
class GlobalRequest(BaseModel):

    # =========================
    # USER PROFILE CORE
    # =========================
    revenus_mensuels: float = Field(default=0, ge=0)
    charges_mensuelles: float = Field(default=0, ge=0)

    # =========================
    # INVESTMENT PROFILE
    # =========================
    budget: float = Field(default=0, ge=0)
    risk: str = Field(default="medium")
    strategy: str = Field(default="balanced")

    # =========================
    # OPTIONAL CONTEXT
    # =========================
    city: str = Field(default="paris")

    # =========================
    # FUTURE EXTENSIONS (SAFE)
    # =========================
    savings: Optional[float] = Field(default=0)
    debts: Optional[float] = Field(default=0)
    investments: Optional[float] = Field(default=0)

    # =========================
    # Pydantic config
    # =========================
    model_config = {
        "extra": "forbid"
    }
