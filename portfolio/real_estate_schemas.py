from typing import Literal, Optional

from pydantic import BaseModel, Field


RealEstateType = Literal["primary_residence", "flip", "rental"]


class RealEstateRequest(BaseModel):
    property_type: RealEstateType
    name: str = Field(min_length=1)
    purchase_price: float = Field(ge=0)
    estimated_value: float = Field(default=0, ge=0)
    resale_price: float = Field(default=0, ge=0)
    monthly_rent: float = Field(default=0, ge=0)
    monthly_charges: float = Field(default=0, ge=0)
    notes: Optional[str] = None

