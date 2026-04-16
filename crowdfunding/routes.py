from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException, Request
from .schemas import CrowdfundingQuery
from .service import get_crowdfunding_intelligence

router = APIRouter()

@router.post("/crowdfunding")
@limiter.limit("20/minute")
def crowdfunding(request: Request, data: CrowdfundingQuery):
    
    def _crowdfunding():
        user_email = request.state.user_email

        return crowdfunding({
            "user_email": user_email,
            **data.dict()
        })
        
    return safe_execute(_crowdfunding, module_name="CROWDFUNDING")
