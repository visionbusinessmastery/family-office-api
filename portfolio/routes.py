from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from .schemas import StockRequest, PortfolioRequest
from portfolio.service import get_user_portfolio
from sqlalchemy import text
from database import engine

router = APIRouter()

# GET PORTFOLIO
@router.get("/")
def get_portfolio(current_user: str = Depends(get_current_user)):
    return get_user_portfolio(current_user)


# ADD ASSET (UPSERT PRO)
@router.post("/portfolio/add")
def add_asset(request: PortfolioRequest, current_user: str = Depends(get_current_user)):

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO portfolios (user_email, asset, asset_type, quantity, buy_price)
                VALUES (:email, :asset, :asset_type, :quantity, :buy_price)
                ON CONFLICT (user_email, asset)
                DO UPDATE SET
                    quantity = portfolios.quantity + EXCLUDED.quantity,
                    buy_price = (
                        (portfolios.quantity * portfolios.buy_price) +
                        (EXCLUDED.quantity * EXCLUDED.buy_price)
                    ) / (portfolios.quantity + EXCLUDED.quantity)
            """), {
                "email": current_user,
                "asset": request.asset.upper(),
                "asset_type": request.asset_type.upper(),
                "quantity": request.quantity,
                "buy_price": request.buy_price
            })

        return {"status": "asset ajouté ou mis à jour"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


  

