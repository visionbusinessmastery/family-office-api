from pydantic import BaseModel

class MarketRequest(BaseModel):
    query: str = "stock market"
