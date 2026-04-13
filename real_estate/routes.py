import logging
from fastapi import APIRouter
from .schemas import RealEstateQuery
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/")
def real(data: RealRequest):
    try:
        result = real_estate_service(data)
        return result

    except Exception as e:
        logging.error(f"REAL ESTATE ERROR: {str(e)}")
        return {
            "status": "error",
            "message": "Erreur dans le module immobilier",
            "details": str(e)
        }
