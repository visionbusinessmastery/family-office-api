from fastapi import APIRouter, Depends, HTTPException
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/real")
def real_estate_intelligence(query: RealEstateQuery):
    return get_real_estate_intelligence(query)
