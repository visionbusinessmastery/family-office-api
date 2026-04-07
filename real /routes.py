from fastapi import APIRouter
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter(prefix="/real-estate", tags=["Real Estate"])

@router.post("/")
def real(query: RealEstateQuery):
    return get_real_estate_intelligence(query)
