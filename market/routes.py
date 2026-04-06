from fastapi import APIRouter, Depends
from auth.utils import get_current_user
from .schemas import MarketRequest
from .service import get_market

router = APIRouter()

@router.post("/market")
def market(request: MarketRequest, user: str = Depends(get_current_user)):
    
    data = get_market(request.query)

    return {
        "user": user,
        "market": data
    }
