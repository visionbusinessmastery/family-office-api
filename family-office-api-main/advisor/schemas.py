from pydantic import BaseModel


class AdvisorRequest(BaseModel):
    message: str
    bypass_cache: bool = False


class AdvisorPremiumRequest(BaseModel):
    message: str
    bypass_cache: bool = False


class AdvisorEliteRequest(BaseModel):
    message: str
    bypass_cache: bool = False
