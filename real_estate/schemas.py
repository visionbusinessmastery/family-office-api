from pydantic import BaseModel

class RealEstateQuery(BaseModel):
    city: str
    strategy: str = "rent"

class RealRequest(BaseModel):
    city: str
    strategy: str
    budget: float
