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
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    cost: Optional[float] = None

    ticker: Optional[str] = None
    gain: Optional[float] = None
    pnl: Optional[float] = None
    gain_percent: Optional[float] = None
    pair_name: Optional[str] = None
    currency_base: Optional[str] = None
    currency_quote: Optional[str] = None

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
    currency_exposure: Optional[list] = None


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
