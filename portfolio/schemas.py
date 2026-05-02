from pydantic import BaseModel, Field
from typing import Optional, List


# =========================
# REQUEST (FRONT → BACKEND)
# =========================
class PortfolioRequest(BaseModel):
    asset_name: str
    asset_type: str
    quantity: float = Field(gt=0)
    purchase_price: float = Field(gt=0)


# =========================
# RESPONSE SINGLE ASSET (IMPORTANT FIX FRONTEND)
# =========================
class PortfolioAsset(BaseModel):
    id: int  # 🔥 CRUCIAL POUR DELETE FRONTEND

    asset_name: str
    asset_type: str

    quantity: float
    purchase_price: float

    value: float

    ticker: Optional[str] = None
    gain: Optional[float] = None
    gain_percent: Optional[float] = None

    source: Optional[str] = None


# =========================
# FULL RESPONSE
# =========================
class PortfolioResponse(BaseModel):
    portfolio: List[PortfolioAsset]

    total_value: float
    total_cost: float
    total_gain: float
    total_gain_percent: float


# =========================
# ANALYSIS (FUTURE AI)
# =========================
class PortfolioAnalysis(BaseModel):
    total_value: float
    total_gain: float
    total_gain_percent: float

    diversification_score: float = 0
    ai_advice: Optional[str] = None
    risk_level: Optional[str] = None
    concentration_warning: Optional[str] = None
