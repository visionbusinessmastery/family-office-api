from pydantic import BaseModel, EmailStr, Field
import time
import yfinance as yf


# ==================================================
# CONFIG STOCK
# ==================================================

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FMP_API_KEY = os.getenv("FMP_API_KEY")

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

