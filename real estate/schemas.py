from pydantic import BaseModel

class RealEstateQuery(BaseModel):
    city: str
    budget: float
    surface_min: float
    strategy: str  # "rent", "flip", "primary"
