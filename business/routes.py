from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from .schemas import BusinessQuery
from .service import get_business_intelligence

router = APIRouter()

@router.post("/business")
def business(query: BusinessQuery):
    return get_business_intelligence(query)
