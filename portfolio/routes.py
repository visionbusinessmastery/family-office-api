from fastapi import APIRouter, Depends
from auth.routes import get_current_user
from portfolio.service import get_user_portfolio

# ==================================================
# CONFIG PROTFOLIO
# ==================================================

router = APIRouter()

# ==================================================
# GET PORTFOLIO
# ==================================================
@router.get("/")
def get_portfolio(user: str = Depends(get_current_user)):
    data = get_user_portfolio(user)
    return {"portfolio": [dict(r._mapping) for r in data]}
