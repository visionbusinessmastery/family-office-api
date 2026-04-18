from pydantic import BaseModel

class ContentRequest(BaseModel):
    budget: float
    risk: str = "medium"
    goal: str = "grow"

class PersonalizedContentRequest(BaseModel):
    goal: str = "grow"
