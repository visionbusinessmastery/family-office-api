from fastapi import APIRouter, Depends
from auth.routes import get_current_user
from ai.service import generate_advice

router = APIRouter()

@router.post("/brain")
def brain(question: str, user: str = Depends(get_current_user)):
    prompt = f"User: {user} Question: {question}"
    answer = generate_advice(prompt)
    return {"answer": answer}
