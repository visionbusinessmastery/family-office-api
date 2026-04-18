from pydantic import BaseModel

class ContentRequest(BaseModel):
    budget: float
    risk: str = "medium"
    goal: str = "grow"
