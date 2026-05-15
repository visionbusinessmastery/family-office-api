# =========================
# GLOBAL FINANCIAL COMMAND CENTER
# =========================

from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.analyzers.financial_overview import get_user_financial_overview

from intelligence.scoring_registry import SCORING_ENGINES

router = APIRouter(prefix="/intelligence", tags=["Global Command Center"])


# =========================
# GET USER ID
# =========================
def get_user_id(conn, email: str):
    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return row.id if row else None


# =========================
# GLOBAL COMMAND CENTER
# =========================
@router.get("/global-command-center")
def global_command_center(user=Depends(get_current_user)):

    email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, email)

        if not user_id:
            return {"error": "User not found"}

        # =========================
        # PROFILE
        # =========================
        profile = {
            "user_id": user_id
        }

        # =========================
        # PORTFOLIO
        # =========================
        portfolio_rows = conn.execute(text("""
            SELECT id, category, quantity, purchase_price
            FROM portfolio
            WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        portfolio = [
            {
                "id": r["id"],
                "type": r["category"],
                "quantity": float(r["quantity"] or 0),
                "purchase_price": float(r["purchase_price"] or 0),
                "value": float((r["quantity"] or 0) * (r["purchase_price"] or 0))
            }
            for r in portfolio_rows
        ]

        # =========================
        # FINANCIAL OVERVIEW
        # =========================
        financial = get_user_financial_overview(user_id)

        # =========================
        # MODULE SCORES
        # =========================
        module_results = {}

        for module_name, engine_fn in SCORING_ENGINES.items():

            try:
                module_results[module_name] = engine_fn(
                    profile=profile,
                    portfolio=portfolio,
                    financial=financial
                )

            except Exception as e:
                module_results[module_name] = {
                    "score": 0,
                    "error": str(e)
                }

        # =========================
        # GLOBAL SCORE
        # =========================
        module_scores = [
            v.get("score", 0)
            for v in module_results.values()
            if isinstance(v, dict)
        ]

        global_score = int(sum(module_scores) / len(module_scores)) if module_scores else 0

        # =========================
        # FINANCIAL FAMILY SCORE (EXISTING CORE)
        # =========================
        family_score = compute_family_office_score(
            profile=profile,
            portfolio=portfolio,
            financial=financial.get("totals", {})
        )

        # =========================
        # FINAL RESPONSE
        # =========================
        return {
            "global_score": global_score,
            "level": family_score["level"],

            "family_office_score": family_score,

            "modules": module_results,

            "financial_overview": financial,

            "portfolio": portfolio,

            "advice": family_score.get("advice", [])
        }
