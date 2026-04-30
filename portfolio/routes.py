from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import PortfolioRequest
from sqlalchemy import text
from database import engine

router = APIRouter()


# =========================
# GET PORTFOLIO (CLEAN)
# =========================
@router.get("/")
@limiter.limit("10/minute")
def get_portfolio(request: Request):

    def _get():

        user_email = request.state.user_email

        with engine.begin() as conn:

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            rows = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolio
                WHERE user_id = :user_id
            """), {"user_id": user.id}).fetchall()

            result = []

            for r in rows:
                result.append({
                    "asset_name": r.asset,
                    "category": r.asset_type,
                    "quantity": float(r.quantity or 0),
                    "purchase_price": float(r.buy_price or 0),
                    "value": float((r.quantity or 0) * (r.buy_price or 0))
                })

            return result

    return safe_execute(_get, module_name="PORTFOLIO")


# =========================
# ADD ASSET (SAFE + NORMALIZED INPUT)
# =========================
@router.post("/portfolio/add")
@limiter.limit("10/minute")
def add_asset(request: Request, data: PortfolioRequest):

    def _add():

        user_email = request.state.user_email

        with engine.begin() as conn:

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            conn.execute(text("""
                INSERT INTO portfolio (
                    user_id,
                    asset,
                    asset_type,
                    quantity,
                    buy_price
                )
                VALUES (
                    :user_id,
                    :asset,
                    :asset_type,
                    :quantity,
                    :buy_price
                )
            """), {
                "user_id": user.id,
                "asset": data.asset.upper().strip(),
                "asset_type": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "buy_price": data.buy_price
            })

        return {"status": "asset ajouté"}

    return safe_execute(_add, module_name="PORTFOLIO")
