from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import BusinessQuery
from .service import get_business_intelligence

router = APIRouter()

@router.post("/business")
@limiter.limit("5/minute")
def business(request: Request, data: BusinessQuery):

    def _business():
        user_email = request.state.user_email

        results = get_business_intelligence(data)

        return {
            "user": user_email,
            "count": len(results),
            "results": results
        }

    return safe_execute(_business, module_name="BUSINESS")
