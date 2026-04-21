from pydantic import BaseModel, Field, EmailStr
from typing import Optional


# =========================
# REGISTER
# =========================
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


# =========================
# PROFILE INPUT
# =========================
class UserProfileRequest(BaseModel):
    genre: Optional[str] = None
    age: Optional[int] = None

    situation_pro: Optional[str] = None
    revenus_mensuels: Optional[float] = 0
    revenus_annuels: Optional[float] = 0

    situation_familiale: Optional[str] = None
    enfants: Optional[bool] = False
    nb_enfants: Optional[int] = 0

    logement: Optional[str] = None
    valeur_bien: Optional[float] = 0
    prix_achat: Optional[float] = 0

    dettes: float = 0
    epargne: float = 0
    investissements: float = 0



# =========================
# SET PASSWORD RECORD
# =========================
class SetPasswordRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
