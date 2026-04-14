from pydantic import BaseModel

class GlobalRequest(BaseModel):
    budget: float
    risk: str
    strategy: str

    model_config = {
        "extra": "forbid"
    }
