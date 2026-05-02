from pydantic import BaseModel


class AdvisorRequest(BaseModel):
    message: str


class AdvisorPremiumRequest(BaseModel):
    message: str


class AdvisorEliteRequest(BaseModel):
    message: str
