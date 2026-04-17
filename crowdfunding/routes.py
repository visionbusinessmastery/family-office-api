from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import CrowdfundingQuery
from .service import get_crowdfunding_intelligence

router = APIRouter()

@router.post("/crowdfunding")
@limiter.limit("20/minute")
def crowdfunding(request: Request, data: CrowdfundingQuery):
    
    def _crowdfunding():
        user_email = request.state.user_email

        result = get_crowdfunding_intelligence(data)

        return {
            "user": user_email,
            "query": {
                "amount": data.amount,
                "duration": data.duration,
                "risk_level": data.risk_level
            },
            "count": len(result) if isinstance(result, list) else 0,
            "results": result
        }
        
    return safe_execute(_crowdfunding, module_name="CROWDFUNDING")
