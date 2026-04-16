from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException, Request
from auth.utils import get_current_user
from .schemas import MarketRequest
from .service import get_market
from .service import get_market_intelligence

router = APIRouter()

@router.post("/market")
@limiter.limit("20/minute")
def market(request: Request, data: MarketRequest):
    
    user_email = request.state.user_email
   
    market_data = get_market(data.query)

    return {
        "user": request.state.user_email,
        "market": result
    }

@router.get("/market-intelligence")
@limiter.limit("20/minute")
def market_intelligence(query: str):
    return get_market_intelligence(query)
