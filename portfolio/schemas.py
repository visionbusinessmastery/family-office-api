from pydantic import BaseModel, Field

# =========================
# REQUESTS
# =========================


class StockRequest(BaseModel):
    ticker: str


class Asset(BaseModel):
    asset: str
    asset_type: str
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)


class PortfolioRequest(BaseModel):
    asset: str
    asset_type: str
    quantity: float = Field(gt=0)
    buy_price: float = Field(gt=0)


# =========================
# RESPONSE / ANALYSIS
# =========================


class PortfolioAnalysis(BaseModel):
    total_value: float
    diversification_score: float
    ai_advice: str
    premium: bool = False

