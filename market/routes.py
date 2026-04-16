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
    
    def _market():
        user_email = request.state.user_email
        market_data = get_market(data.query)

        return market({
            "user_email": user_email,
            **data.dict()
        })

        return {
            "user": request.state.user_email,
            "market": result
        }

    return safe_execute(_market, module_name="MARKET")


@router.get("/market-intelligence")
@limiter.limit("20/minute")
def market_intelligence(request: Request, query: str):
    
    def _market_intelligence():
        user_email = request.state.user_email

        return market_intelligence({
            "user_email": user_email,
            **data.dict()
        })
    
        return get_market_intelligence(query)
    
    return safe_execute(_market_intelligence, module_name="MARKET_INTELLIGENCE")
    
