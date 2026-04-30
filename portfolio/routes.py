from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request
from .schemas import PortfolioRequest
from sqlalchemy import text
from database import engine

router = APIRouter()

# =========================
# GET PORTFOLIO (FIXED)
# =========================
@router.get("/")
@limiter.limit("10/minute")
def get_portfolio(request: Request):

    def _get():
        user_email = request.state.user_email

        with engine.begin() as conn:

            # 🔥 GET USER ID
            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            user_id = user.id

            # 🔥 GET PORTFOLIO
            portfolio = conn.execute(text("""
                SELECT asset_name, category, quantity, purchase_price
                FROM portfolio
                WHERE user_id = :user_id
            """), {"user_id": user_id}).fetchall()

            result = []

            for p in portfolio:
                result.append({
                    "asset_name": p.asset_name,
                    "category": p.category,
                    "quantity": float(p.quantity or 0),
                    "purchase_price": float(p.purchase_price or 0),
                    "value": float((p.quantity or 0) * (p.purchase_price or 0))
                })

            print("🔥 GET PORTFOLIO:", result)

            return result

    return safe_execute(_get, module_name="PORTFOLIO")


# =========================
# ADD ASSET (OK + CLEAN)
# =========================
@router.post("/portfolio/add")
@limiter.limit("10/minute")
def add_asset(request: Request, data: PortfolioRequest):

    def _add():

        user_email = request.state.user_email

        with engine.begin() as conn:

            # 🔥 GET USER ID
            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            user_id = user.id

            # 🔥 INSERT (NO DUPLICATE LOGIC YET)
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
