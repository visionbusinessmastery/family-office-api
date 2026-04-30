from pydantic import BaseModel, Field
from typing import Optional, List


# =========================
# REQUEST
# =========================
class PortfolioRequest(BaseModel):
    asset: str
    asset_type: str
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)


# =========================
# SINGLE ASSET RESPONSE
# =========================
class PortfolioAsset(BaseModel):
    asset: str
    ticker: Optional[str] = None
    type: str

    quantity: float
    buy_price: float
    current_price: float

    value: float
    gain: float
    gain_percent: float

    source: Optional[str] = None


# =========================
# FULL PORTFOLIO RESPONSE
# =========================
class PortfolioResponse(BaseModel):
    portfolio: List[PortfolioAsset]

    total_value: float
    total_cost: float
    total_gain: float
    total_gain_percent: float


# =========================
# ANALYSIS (FUTURE AI LAYER)
# =========================
class PortfolioAnalysis(BaseModel):
    total_value: float
    total_gain: float
    total_gain_percent: float

    diversification_score: float = 0
    ai_advice: Optional[str] = None
    risk_level: Optional[str] = None
    concentration_warning: Optional[str] = None
