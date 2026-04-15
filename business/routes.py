from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from .schemas import BusinessQuery
from .service import get_business_intelligence

router = APIRouter()

@router.post("/business")
@limiter.limit("5/minute")
def business(request: Request, query: BusinessQuery):
    return get_business_intelligence(query)
