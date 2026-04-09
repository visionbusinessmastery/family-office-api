from pydantic import BaseModel

class RealEstateQuery(BaseModel):
    city: str
    strategy: str = "rent"
