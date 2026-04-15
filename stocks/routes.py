from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from .schemas import StockRequest
from .service import get_stock_data

router = APIRouter()

@router.post("/stocks/search")
@limiter.limit("20/minute")
def search_stocks(request: Request, request: StockRequest, user: str = Depends(get_current_user)):

    data = get_stock_data(request.query)
