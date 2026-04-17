from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import RealRequest
from .service import get_real_estate_intelligence

router = APIRouter()

@router.post("/")
@limiter.limit("5/minute")
def real(request: Request, data: RealRequest):

    def _real():
        user_email = request.state.user_email

        result = get_real_estate_intelligence(data)

        return {
            "user": user_email,
            "query": {
                "city": data.city,
                "strategy": data.strategy,
                "budget": data.budget,
                "surface_min": data.surface_min
            },
            "count": len(result) if isinstance(result, list) else 0,
            "results": result
        }

    return safe_execute(_real, module_name="REAL_ESTATE")
