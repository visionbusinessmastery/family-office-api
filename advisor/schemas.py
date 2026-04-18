from pydantic import BaseModel

class AdvisorRequest(BaseModel):
    message: str  # ex: "j’ai 10k que faire"
