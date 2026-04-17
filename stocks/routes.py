from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import StockRequest
from .service import get_stock_data

router = APIRouter()

@router.post("/stocks/search")
@limiter.limit("20/minute")
def search_stock(request: Request, data: StockRequest):

    def _search():
        user_email = request.state.user_email

        result = get_stock_data(data.query)

        return {
            "user": user_email,
            "result": result
        }

    return safe_execute(_search, module_name="STOCKS")
