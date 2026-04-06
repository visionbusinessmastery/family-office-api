from fastapi import APIRouter, Depends, HTTPException
from auth.utils import get_current_user
from .schemas import StockRequest, PortfolioRequest
from portfolio.service import get_user_portfolio
from sqlalchemy import text
from database import engine

router = APIRouter()

# GET PORTFOLIO
@router.get("/")
def get_user_portfolio(email):
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
        asset = r[0]
        asset_type = r[1]
        quantity = r[2]
        buy_price = r[3]

        value = quantity * buy_price
        cost = quantity * buy_price

        total_value += value
        total_cost += cost

        portfolio.append({
            "asset": asset,
            "type": asset_type,
            "quantity": quantity,
            "buy_price": buy_price,
            "value": value
        })

    return {
        "portfolio": portfolio,
        "total_value": total_value,
        "total_cost": total_cost
    }


# ADD ASSET (UPSERT PRO)
@router.post("/portfolio/add")
def add_asset(request: PortfolioRequest, current_user: str = Depends(get_current_user)):

    try:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


  

