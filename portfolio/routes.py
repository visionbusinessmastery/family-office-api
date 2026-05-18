# =========================
# IMPORTS
# =========================
from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, HTTPException, Request
from .schemas import PortfolioRequest
from sqlalchemy import text
from database import engine
from workspaces.routes import resolve_workspace_context

from .service import (
    get_user_portfolio,
    invalidate_portfolio_cache,
    save_portfolio_snapshot,
)

router = APIRouter()


def get_user_or_404(conn, email: str):
    user = conn.execute(text("""
        SELECT id FROM users WHERE email = :email
    """), {"email": email}).fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def refresh_portfolio_side_effects(user_id: int, email: str):
    invalidate_portfolio_cache(user_id, email)
    save_portfolio_snapshot(user_id)

# =========================
# GET PORTFOLIO
# =========================
@router.get("/")
@limiter.limit("10/minute")
def get_portfolio(request: Request):

    def _get():
        user_email = request.state.user_email

        with engine.begin() as conn:

            workspace = resolve_workspace_context(conn, request, user_email)

            return get_user_portfolio(workspace["user_id"], use_cache=False)

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

            workspace = resolve_workspace_context(conn, request, user_email, write=True)

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
                "user_id": workspace["user_id"],
                "asset_name": data.asset_name.upper().strip(),
                "category": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "purchase_price": data.purchase_price
            })
            
            user_id = workspace["user_id"]
            cache_email = workspace["email"]

        refresh_portfolio_side_effects(user_id, cache_email)
        
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

            workspace = resolve_workspace_context(conn, request, user_email, write=True)

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
                "user_id": workspace["user_id"],
                "asset_name": data.asset_name.upper().strip(),
                "category": data.asset_type.upper().strip(),
                "quantity": data.quantity,
                "purchase_price": data.purchase_price
            })

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="Asset not found")

            user_id = workspace["user_id"]
            cache_email = workspace["email"]

        refresh_portfolio_side_effects(user_id, cache_email)

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

            workspace = resolve_workspace_context(conn, request, user_email, write=True)

            result = conn.execute(text("""
                DELETE FROM portfolio
                WHERE id = :asset_id AND user_id = :user_id
            """), {
                "asset_id": asset_id,
                "user_id": workspace["user_id"]
            })

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Asset not found or not owned by user",
                )

            user_id = workspace["user_id"]
            cache_email = workspace["email"]

        refresh_portfolio_side_effects(user_id, cache_email)

        return {"status": "deleted", "id": asset_id}

    return safe_execute(_delete, module_name="PORTFOLIO")


# =========================
# PORTFOLIO HISTORY
# =========================
@router.get("/history")
def portfolio_history(request: Request):

    user_email = request.state.user_email

    with engine.begin() as conn:
        workspace = resolve_workspace_context(conn, request, user_email)

        total_cost = conn.execute(text("""
            SELECT COALESCE(SUM(quantity * purchase_price), 0)
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": workspace["user_id"]}).scalar()

        rows = conn.execute(text("""
            SELECT total_value, created_at
            FROM portfolio_history
            WHERE user_id = :user_id
            ORDER BY created_at ASC
        """), {"user_id": workspace["user_id"]}).fetchall()

    return {
        "history": [
            {
                "date": r.created_at.isoformat(),
                "value": float(r.total_value),
                "cost": float(total_cost or 0),
                "gain": float(r.total_value) - float(total_cost or 0)
            }
            for r in rows
        ]
    }
