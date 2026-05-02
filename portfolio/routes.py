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
                    "id": r.id,
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
@router.post("/")
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


# =========================
# UPDATE ASSET
# =========================
@router.put("/{asset_id}")
@limiter.limit("10/minute")
def update_asset(request: Request, asset_id: int, data: PortfolioRequest):

    def _update():
        user_email = request.state.user_email

        with engine.begin() as conn:

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            result = conn.execute(text("""
                UPDATE portfolio
                SET
                    asset_name = :asset_name,
                    category = :category,
                    quantity = :quantity,
                    purchase_price = :purchase_price
                WHERE id = :asset_id
                AND user_id = :user_id
            """), {
                "asset_id": asset_id,
                "user_id": user.id,
                "asset_name": data.asset_name.upper().strip(),
                "category": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "purchase_price": data.purchase_price
            })

            if result.rowcount == 0:
                raise Exception("Asset not found")

        return {"status": "updated", "id": asset_id}

    return safe_execute(_update, module_name="PORTFOLIO")


# =========================
# DELETE ASSET
# =========================
@router.delete("/{asset_id}")
@limiter.limit("10/minute")
def delete_asset(request: Request, asset_id: int):

    def _delete():
        user_email = request.state.user_email

        with engine.begin() as conn:

            user = conn.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user:
                raise Exception("User not found")

            result = conn.execute(text("""
                DELETE FROM portfolio
                WHERE id = :asset_id AND user_id = :user_id
            """), {
                "asset_id": asset_id,
                "user_id": user.id
            })

            if result.rowcount == 0:
                raise Exception("Asset not found or not owned by user")

        return {"status": "deleted", "id": asset_id}

    return safe_execute(_delete, module_name="PORTFOLIO")


# =========================
# PORTFOLIO HISTORY
# =========================
@router.get("/portfolio/history")
def portfolio_history(request: Request):

    user_email = request.state.user_email

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT total_value, created_at
            FROM portfolio_history ph
            JOIN users u ON u.id = ph.user_id
            WHERE u.email = :email
            ORDER BY created_at ASC
        """), {"email": user_email}).fetchall()

    return {
        "history": [
            {
                "date": r.created_at,
                "value": r.total_value
            }
            for r in rows
        ]
    }
