from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# ==================================================
# MODELS
# ==================================================

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

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

    dettes: Optional[dict] = {}
    epargne: Optional[dict] = {}
    investissements: Optional[dict] = {}

class UserProfile(BaseModel):
    genre: Optional[str] = None
    age: Optional[int] = None
    situation_pro: Optional[str] = None
    revenus_mensuels: Optional[float] = None
    revenus_annuels: Optional[float] = None
    situation_familiale: Optional[str] = None
    enfants: Optional[bool] = None
    nb_enfants: Optional[int] = None
    logement: Optional[str] = None
    valeur_bien: Optional[float] = None
    prix_achat: Optional[float] = None
    dettes: Optional[Dict] = {}
    epargne: Optional[Dict] = {}
    investissements: Optional[Dict] = {}
    
