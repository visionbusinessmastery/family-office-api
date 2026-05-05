from core.limiter import limiter
from fastapi import APIRouter, Request
from core.utils import safe_execute

from .schemas import GlobalRequest
from .service import get_global_intelligence, get_family_office_score

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision
from sqlalchemy import text
from database import engine

from intelligence.user_intelligence_engine import compute_user_intelligence

router = APIRouter()


# =========================
# GLOBAL INTELLIGENCE
# =========================
@router.post("/global")
@limiter.limit("5/minute")
def global_intelligence(request: Request, data: GlobalRequest):

    def _global_intelligence():
        user_email = request.state.user_email

        result = get_global_intelligence(data)

        return {
            "user": user_email,
            "query": {
                "budget": data.budget,
                "risk": data.risk,
                "strategy": data.strategy,
                "city": data.city
            },
            "result": result
        }

    return safe_execute(_global_intelligence, module_name="GLOBAL_INTELLIGENCE")


# =========================
# FAMILY OFFICE SCORE
# =========================
@router.get("/family-office-score")
def family_office_score(request: Request):

    def _score():
        user_email = request.state.user_email

        result = get_family_office_score(user_email)

        return {
            "user": user_email,
            "family_office_index": result
        }

    return safe_execute(_score, module_name="FAMILY_OFFICE_SCORE")


# =========================
# USER UPGRADE CHECK
# =========================
@router.get("/user/upgrade-check")
def user_upgrade_check(request: Request):

    def _upgrade_check():

        user_email = request.state.user_email

        with engine.begin() as conn:

            # =========================
            # USER
            # =========================
            user_data = conn.execute(text("""
                SELECT plan
                FROM users
                WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user_data:
                raise Exception("User not found")

            # =========================
            # PROFILE
            # =========================
            profile = conn.execute(text("""
                SELECT 
                    savings,
                    investments,
                    risk_profile
                FROM user_profiles
                WHERE user_email = :email
            """), {"email": user_email}).fetchone()

            profile_dict = dict(profile._mapping) if profile else {}

            # =========================
            # PORTFOLIO
            # =========================
            portfolio_rows = conn.execute(text("""
                SELECT asset_name, asset_type, quantity, purchase_price
                FROM portfolio
                WHERE user_email = :email
            """), {"email": user_email}).fetchall()

            portfolio = []
            for p in portfolio_rows:
                qty = float(p.quantity or 0)
                price = float(p.purchase_price or 0)

                portfolio.append({
                    "asset_name": p.asset_name,
                    "type": p.asset_type,
                    "value": qty * price
                })

            # =========================
            # SCORE
            # =========================
            score_data = compute_family_office_score(
                profile_dict,
                portfolio
            )

            # =========================
            # UPGRADE DECISION
            # =========================
            decision = compute_upgrade_decision(
                current_plan=user_data.plan,
                score=score_data["score"]
            )

            # =========================
            # SAVE RECOMMENDATION
            # =========================
            conn.execute(text("""
                UPDATE users
                SET recommended_plan = :recommended,
                    last_score_update = NOW()
                WHERE email = :email
            """), {
                "recommended": decision["recommended_plan"],
                "email": user_email
            })

            # =========================
            # SAFE AUTO UPGRADE (FIXED BUG)
            # =========================
            if decision.get("upgrade") and decision.get("to") == "ELITE":

                conn.execute(text("""
                    UPDATE users
                    SET plan = :plan,
                        subscription_status = 'active'
                    WHERE email = :email
                """), {
                    "plan": decision["to"],
                    "email": user_email
                })

            return {
                "user": user_email,
                "score": score_data["score"],
                "details": score_data.get("details", {}),
                "advice": score_data.get("advice", []),
                "current_plan": user_data.plan,
                "upgrade": decision
            }

    return safe_execute(_upgrade_check, module_name="USER_UPGRADE_CHECK")


# =========================
# USER INTELLIGENCE
# =========================
@router.get("/user-intelligence")
def user_intelligence(request: Request):

    def _engine():
        user_email = request.state.user_email
        return compute_user_intelligence(user_email)

    return safe_execute(_engine, module_name="USER_INTELLIGENCE")


# =========================
# RUN PIPELINE
# =========================
@router.get("/run")
def run_intelligence(request: Request):

    def _run():
        user_email = request.state.user_email

        result = compute_user_intelligence(user_email)

        return {
            "user": user_email,
            "intelligence": result
        }

    return safe_execute(_run, module_name="USER_INTELLIGENCE_PIPELINE")
