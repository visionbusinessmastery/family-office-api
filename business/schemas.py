from pydantic import BaseModel

class BusinessQuery(BaseModel):
    mode: str  # "create", "grow", "buy"
    sector: str
    budget: float
    location: str
