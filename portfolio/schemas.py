from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict
from database import Base
from sqlalchemy import Column, Integer, String, Float

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

class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True)
    asset = Column(String)
    asset_type = Column(String)
    quantity = Column(Integer)
    buy_price = Column(Float)
    
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
