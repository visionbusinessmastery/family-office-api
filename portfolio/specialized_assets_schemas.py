from typing import Literal, Optional

from pydantic import BaseModel, Field


YieldAssetType = Literal["crowdfunding", "private_equity"]
VentureAssetType = Literal["ai_business", "business", "startup", "franchise"]


class YieldAssetRequest(BaseModel):
    asset_type: YieldAssetType
    name: str = Field(min_length=1)
    principal: float = Field(ge=0)
    average_rate: float = Field(default=0, ge=0)
    duration_months: int = Field(default=12, ge=1)
    notes: Optional[str] = None


class VentureAssetRequest(BaseModel):
    asset_type: VentureAssetType
    name: str = Field(min_length=1)
    revenue: float = Field(default=0, ge=0)
    charges: float = Field(default=0, ge=0)
    fundraising: float = Field(default=0, ge=0)
    debts: float = Field(default=0, ge=0)
    valuation: float = Field(default=0, ge=0)
    notes: Optional[str] = None

