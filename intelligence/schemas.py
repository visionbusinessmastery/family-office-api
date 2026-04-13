from pydantic import BaseModel

class GlobalQuery(BaseModel):
    budget: float
    risk: str  # low, medium, high
    strategy: str  # growth, income, balanced
