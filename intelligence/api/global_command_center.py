# =========================
# GLOBAL FINANCIAL COMMAND CENTER API V2
# =========================

from fastapi import APIRouter, Depends
from sqlalchemy import text

from database import engine
from auth.utils import get_current_user

from intelligence.engines.global_financial_command_center import (
    compute_global_command_center
)

from intelligence.analyzers.financial_overview import (
    get_user_financial_overview
)

router = APIRouter(
    prefix="/intelligence",
    tags=["Global Command Center"]
)


# =========================
# GET USER ID
# =========================
def get_user_id(conn, email: str):

    row = conn.execute(
        text("""
            SELECT id
            FROM users
            WHERE email = :email
        """),
        {"email": email}
    ).fetchone()

    return row.id if row else None


# =========================
# LOAD PORTFOLIO
# =========================
def load_portfolio(conn, user_id: int):

    rows = conn.execute(text("""
        SELECT
            id,
            category,
            quantity,
            purchase_price
        FROM portfolio
        WHERE user_id = :user_id
    """), {
        "user_id": user_id
    }).mappings().all()

    portfolio = []

    for r in rows:

        quantity = float(r["quantity"] or 0)
        purchase_price = float(r["purchase_price"] or 0)

        portfolio.append({
            "id": r["id"],
            "type": r["category"],
            "quantity": quantity,
            "purchase_price": purchase_price,
            "value": quantity * purchase_price,
        })

    return portfolio


# =========================
# LOAD ONBOARDING
# =========================
def load_onboarding(conn, user_id: int):

    row = conn.execute(text("""
        SELECT
            revenus_mensuels,
            charges_mensuelles,
            risk_profile
        FROM onboarding
        WHERE user_id = :user_id
    """), {
        "user_id": user_id
    }).mappings().fetchone()

    if not row:
        return {}

    return {
        "revenus_mensuels": float(
            row.get("revenus_mensuels") or 0
        ),

        "charges_mensuelles": float(
            row.get("charges_mensuelles") or 0
        ),

        "risk_profile": (
            row.get("risk_profile") or "medium"
        )
    }


# =========================
# GLOBAL COMMAND CENTER
# =========================
@router.get("/global-command-center")
def global_command_center(
    user=Depends(get_current_user)
):

    try:

        email = user

        with engine.connect() as conn:

            # =========================
            # USER ID
            # =========================
            user_id = get_user_id(conn, email)

            if not user_id:
                return {
                    "error": "User not found"
                }

            # =========================
            # USER OBJECT
            # =========================
            user_object = {
                "id": user_id,
                "email": email,
            }

            # =========================
            # LOAD DATA
            # =========================
            onboarding = load_onboarding(
                conn,
                user_id
            )

            portfolio = load_portfolio(
                conn,
                user_id
            )

            financial_overview = (
                get_user_financial_overview(
                    user_id
                )
            )

            # =========================
            # GLOBAL ENGINE
            # =========================
            result = compute_global_command_center(
                user=user_object,
                onboarding=onboarding,
                portfolio=portfolio,
                financial_overview=financial_overview,
            )

            # =========================
            # FRONTEND READY
            # =========================
            return {
                "success": True,

                "global_score": result.get(
                    "global_score",
                    0
                ),

                "level": result.get(
                    "level",
                    "BEGINNER"
                ),

                "modules": result.get(
                    "modules",
                    {}
                ),

                "advice": result.get(
                    "advice",
                    []
                ),

                "context": result.get(
                    "context",
                    {}
                ),

                "portfolio": portfolio,

                "financial_overview": (
                    financial_overview
                ),

                "onboarding": onboarding,
            }

    except Exception as e:

        return {
            "success": False,
            "error": str(e),
        }
