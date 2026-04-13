from core.utils import safe_execute
from fastapi import APIRouter
from .schemas import RealRequest
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/")
def real(data: RealRequest):

    def _real():
        return get_real_estate_intelligence(data)

    return safe_execute(_real, module_name="REAL_ESTATE")
