from pydantic import BaseModel

class CrowdfundingQuery(BaseModel):
    amount: float
    duration: int  # mois
    risk_level: str  # low / medium / high
