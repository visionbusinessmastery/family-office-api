from typing import Literal

from pydantic import BaseModel


class BusinessQuery(BaseModel):
    mode: Literal["create", "grow", "buy"]
    sector: str
    budget: float
    location: str
