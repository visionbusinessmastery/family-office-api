from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import PortfolioRequest
from portfolio.service import get_user_portfolio
from sqlalchemy import text
from database import engine

router = APIRouter()

# =========================
# GET PORTFOLIO
# =========================
@router.get("/")
@limiter.limit("10/minute")
def get_portfolio(request: Request):

    def _get():
        user_email = request.state.user_email
        return get_user_portfolio(user_email)

    return safe_execute(_get, module_name="PORTFOLIO")


# =========================
# ADD ASSET (FIXED)
# =========================
@router.post("/portfolio/add")
@limiter.limit("10/minute")
def add_asset(request: Request, data: PortfolioRequest):

    def _add():

        user_id = request.state.user_id

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO portfolio (
                    user_id,
                    asset_name,
                    category,
                    quantity,
                    purchase_price
                )
                VALUES (
                    :user_id,
                    :asset_name,
                    :category,
                    :quantity,
                    :purchase_price
                )
            """), {
                "user_id": user_id,
                "asset_name": data.asset.upper(),
                "category": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "purchase_price": data.buy_price
            })

        return {"status": "asset ajouté"}

    return safe_execute(_add, module_name="PORTFOLIO")

    return safe_execute(_add, module_name="PORTFOLIO")
  

