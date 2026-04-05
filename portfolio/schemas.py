from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict

# ==================================================
# MODELS
# ==================================================

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
    
class PortfolioAnalysis(BaseModel):
    total_value: float
    diversification_score: float
    ai_advice: str
    premium: bool = False  # Si premium, créer opportunité CRM
