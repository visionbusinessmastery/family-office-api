from fastapi import APIRouter, Depends, HTTPException
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/")
def real(query: RealEstateQuery):
    return get_real_estate_intelligence(query)
