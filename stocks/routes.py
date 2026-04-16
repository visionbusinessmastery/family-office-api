from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException, Request
from auth.utils import get_current_user
from .schemas import StockRequest
from .service import get_stock_data

router = APIRouter()

@router.post("/stocks/search")
@limiter.limit("20/minute")
def search_stocks(request: Request, data: StockRequest):
    
    def _search_stock():
        user_email = request.state.user_email

        return get_stock({
            "user_email": user_email,
            **data.dict()
        })

        return result
        
    return safe_execute(_search_stock, module_name="SEARCH_STOCK")
