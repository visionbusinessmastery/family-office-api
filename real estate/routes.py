from fastapi import APIRouter
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/real-estate")
def real_estate_intelligence(query: RealEstateQuery):
    return get_real_estate_intelligence(query)
