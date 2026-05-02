from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import PortfolioRequest
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

        with engine.begin() as conn:

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            rows = conn.execute(text("""
                SELECT id, asset_name, category, quantity, purchase_price
                FROM portfolio
                WHERE user_id = :user_id
            """), {"user_id": user.id}).fetchall()

            result = []

            for r in rows:
                result.append({
                    "id": r.id,  # 🔥 IMPORTANT
                    "asset_name": r.asset_name,
                    "asset_type": r.category,
                    "quantity": float(r.quantity or 0),
                    "purchase_price": float(r.purchase_price or 0),
                    "value": float((r.quantity or 0) * (r.purchase_price or 0))
                })

            return {"portfolio": result}

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

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

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
                "user_id": user.id,
                "asset_name": data.asset_name.upper().strip(),
                "category": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "purchase_price": data.purchase_price
            })

        return {"status": "asset ajouté"}

    return safe_execute(_add, module_name="PORTFOLIO")
