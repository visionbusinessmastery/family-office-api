from pydantic import BaseModel

class GlobalRequest(BaseModel):
    budget: float
    risk: str
    strategy: str
    city: str = "paris"
    
    model_config = {
        "extra": "forbid"
    }
