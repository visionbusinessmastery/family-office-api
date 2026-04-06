from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from .schemas import StockRequest
from .service import get_stock_data

router = APIRouter()

@router.post("/stocks/search")
def search_stock(request: StockRequest, user: str = Depends(get_current_user)):

    data = get_stock_data(request.query)

    if not data or "error" in data:
        raise HTTPException(status_code=400, detail=data.get("error", "Erreur"))

    return data
