from pydantic import BaseModel

# =========================
# REQUEST
# =========================

class BrainRequest(BaseModel):
    question: str

