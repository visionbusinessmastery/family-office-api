from fastapi import APIRouter, Depends
from auth.utils import get_current_user
from .schemas import MarketRequest
from .service import get_market_intelligence

router = APIRouter()

@router.post("/intelligence")
def market_intelligence(request: MarketRequest, user: str = Depends(get_current_user)):
    
    data = get_market_intelligence(request.query)

    return {
        "user": user,
        "market_intelligence": data
    }
