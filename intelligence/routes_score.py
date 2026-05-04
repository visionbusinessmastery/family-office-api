# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from sqlalchemy import text
from database import engine
from auth.utils import get_current_user

from intelligence.analyzers.family_office_score import compute_family_office_score

router = APIRouter()

# =========================
# GET USER ID
# =========================
def get_user_id(conn, email):
    row = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email}
    ).fetchone()

    return row.id if row else None

# =========================
# RECALCULATE SCORE
# =========================
@router.post("/score/recalculate")
def recalculate_score(user=Depends(get_current_user)):

    user_email = user

    with engine.connect() as conn:

        user_id = get_user_id(conn, user_email)

        if not user_id:
            return {"error": "User not found"}

        # =========================
        # GET FINANCE DATA
        # =========================
        rows = conn.execute(
            text("""
                SELECT type, amount
                FROM finance_items
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        ).fetchall()

    # =========================
    # AGGREGATION
    # =========================
    total_income = sum(r.amount for r in rows if r.type == "revenus")
    total_debt = sum(r.amount for r in rows if r.type == "dettes")
    total_savings = sum(r.amount for r in rows if r.type == "epargne")

    financial = {
        "cashflow_score": min(total_income / 100, 100) if total_income else 0,
        "debt_risk_score": min(total_debt / 100, 100) if total_debt else 0,
        "savings_velocity_score": min(total_savings / 100, 100) if total_savings else 0,
        "income_stability_score": 60  # placeholder simple
    }

    # =========================
    # FAKE PROFILE + PORTFOLIO (à adapter)
    # =========================
    profile = {
        "savings": total_savings,
        "investments": 0,
        "risk_profile": "medium"
    }

    portfolio = []

    # =========================
    # SCORE
    # =========================
    result = compute_family_office_score(profile, portfolio, financial)

    return result
