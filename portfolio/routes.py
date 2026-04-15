from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException, Request
from auth.utils import get_current_user
from .schemas import StockRequest, PortfolioRequest
from portfolio.service import get_user_portfolio
from sqlalchemy import text
from database import engine

router = APIRouter()

# GET PORTFOLIO
@router.get("/")
@limiter.limit("10/minute")
def get_user_portfolio(request: Request, data: PortfolioRequest):

    def _get():
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolios
                WHERE user_email=:email
            """), {"email": email})

            rows = result.fetchall()

        portfolio = []
        total_value = 0
        total_cost = 0

        for r in rows:
            value = r[2] * r[3]

            total_value += value
            total_cost += value

            portfolio.append({
                "asset": r[0],
                "type": r[1],
                "quantity": r[2],
                "buy_price": r[3],
                "value": value
            })

        return {
            "portfolio": portfolio,
            "total_value": total_value,
            "total_cost": total_cost
        }

    return safe_execute(_get, module_name="PORTFOLIO")


# ADD ASSET (UPSERT PRO)
@router.post("/portfolio/add")
@limiter.limit("10/minute")
def add_asset(request: Request, data: PortfolioRequest):

    def _add():
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
                "email": current_user,
                "asset": request.asset.upper(),
                "asset_type": request.asset_type.upper().replace(",", "").strip(),
                "quantity": request.quantity,
                "buy_price": request.buy_price
            })

        return {"status": "asset ajouté ou mis à jour"}

    return safe_execute(_add, module_name="PORTFOLIO")
  

