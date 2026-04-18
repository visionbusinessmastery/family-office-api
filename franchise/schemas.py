from pydantic import BaseModel
from typing import Optional

class FranchiseRequest(BaseModel):
    budget: float
    country: str = "france"
    risk: Optional[str] = "medium"
    sector: Optional[str] = None
