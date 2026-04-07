from fastapi import APIRouter
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter(prefix="/real", tags=["Real"])

@router.post("/real")
def real(query: RealQuery):
    return get_real(query)
