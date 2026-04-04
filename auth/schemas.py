from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Optional, str

# ==================================================
# MODELS
# ==================================================

class ProfileRequest(BaseModel):
    email: Optional[str] = None
    revenus: float
    charges: float
    epargne: float
    immobilier: float
    investissements: float
    crypto: float
    risque: str
    experience: str

class BrainRequest(BaseModel):
    question: str

class StockRequest(BaseModel):
    ticker: str

class Asset(BaseModel):
    asset: str
    asset_type: str
    quantity: float
    buy_price: float 

class PortfolioRequest(BaseModel):
    asset: str
    asset_type: str
    quantity: float
    buy_price: float

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class ProfileRequest(BaseModel):
    gender: str
    age: int

    employment_status: str
    monthly_income: float

    marital_status: str
    children_count: int

    housing_status: str
    real_estate_value: float = 0
    real_estate_purchase_price: float = 0

    total_debt: float = 0

    savings: float = 0
    investments: float = 0
    crypto: float = 0

    risk_profile: str

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
    
class PortfolioAnalysis(BaseModel):
    total_value: float
    diversification_score: float
    ai_advice: str
    premium: bool = False  # Si premium, créer opportunité CRM
