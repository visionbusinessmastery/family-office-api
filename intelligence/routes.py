from core.limiter import limiter
from fastapi import APIRouter, Request
from core.utils import safe_execute

from .schemas import GlobalRequest
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
@limiter.limit("5/minute")
def global_intelligence(request: Request, data: GlobalRequest):   

    def _global_intelligence():
        user_email = request.state.user_email

        result = get_global_intelligence(data)

        return {
            "user": user_email,
            "query": {
                "budget": data.budget,
                "risk": data.risk,
                "strategy": data.strategy
            },
            "result": result
        }
    
    return safe_execute(_global_intelligence, module_name="GLOBAL_INTELLIGENCE")

