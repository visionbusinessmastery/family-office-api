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
# ADD ASSET
# =========================
@router.post("/portfolio/add")
@limiter.limit("10/minute")
def add_asset(request: Request, data: PortfolioRequest):

    def _add():
        user_email = request.state.user_email

        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
                VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
                ON CONFLICT ON CONSTRAINT unique_user_asset
                DO UPDATE SET
                    quantity = portfolios.quantity + EXCLUDED.quantity,
                    buy_price = (
                        (portfolios.quantity * portfolios.buy_price) +
                        (EXCLUDED.quantity * EXCLUDED.buy_price)
                    ) / (portfolios.quantity + EXCLUDED.quantity)
            """), {
                "email": user_email,
                "asset": data.asset.upper(),
                "asset_type": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "buy_price": data.buy_price
            })

        return {"status": "asset ajouté ou mis à jour"}

    return safe_execute(_add, module_name="PORTFOLIO")
  

