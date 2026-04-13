from pydantic import BaseModel

class CryptoQuery(BaseModel):
    symbol: str  # BTC, ETH, SOL
    strategy: str  # "hold", "trade", "long_term"
