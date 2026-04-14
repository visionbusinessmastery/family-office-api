from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from .schemas import CrowdfundingQuery
from .service import get_crowdfunding_intelligence

router = APIRouter()

@router.post("/crowdfunding")
@limiter.limit("20/minute")
def crowdfunding(query: CrowdfundingQuery):
    return get_crowdfunding_intelligence(query)
