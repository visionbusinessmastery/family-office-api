from core.limiter import limiter
from fastapi import APIRouter, Request
from core.utils import safe_execute

from .schemas import GlobalRequest
from .service import get_global_intelligence

from .service import get_family_office_score

from intelligence.analyzers.family_office_score import compute_family_office_score
from intelligence.upgrade_engine import compute_upgrade_decision
from sqlalchemy import text
from database import engine

from intelligence.user_intelligence_engine import compute_user_intelligence


router = APIRouter()


# =========================
# GLOBAL
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
# FAMILY OFFICE SOCRE
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
            # GET USER PLAN
            # =========================
            user_data = conn.execute(text("""
                SELECT plan
                FROM users
                WHERE email = :email
            """), {"email": user_email}).fetchone()

            if not user_data:
                raise Exception("User not found")

            # =========================
            # GET USER PROFILE
            # =========================
            profile = conn.execute(text("""
                SELECT 
                    savings,
                    investments,
                    total_debt,
                    real_estate_value,
                    risk_profile
                FROM user_profiles
                WHERE user_email = :email
            """), {"email": user_email}).fetchone()

            profile_dict = profile._asdict() if profile else {}

            # =========================
            # PORTFOLIO (TEMPORAIRE)
            # =========================
            portfolio = []

            # =========================
            # SCORE ENGINE
            # =========================
            score_data = compute_family_office_score(
                profile_dict,
                portfolio
            )

            # =========================
            # UPGRADE ENGINE
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
            # AUTO UPGRADE SAFE MODE (ONLY ELITE)
            # =========================
            if decision["auto_apply"]:

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
                "details": score_data["details"],
                "advice": score_data["advice"],
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

        result = compute_user_intelligence(user_email)

        # ✅ FIX CRITIQUE → PAS DE NESTING
        return result

    return safe_execute(_engine, module_name="USER_INTELLIGENCE")


# =========================
# RUN INTELLIGENCE
# =========================
@router.get("/run")
def run_intelligence(request: Request):

    def _run():
        user_email = request.state.user_email

        # DB FETCH SAFE
        with engine.begin() as conn:

            profile = conn.execute(text("""
                SELECT *
                FROM user_profiles
                WHERE user_email = :email
            """), {"email": user_email}).fetchone()

            profile_dict = dict(profile._mapping) if profile else {}

            user = conn.execute(text("""
                SELECT plan
                FROM users
                WHERE email = :email
            """), {"email": user_email}).fetchone()

            portfolio = conn.execute(text("""
                SELECT asset_name, type, value
                FROM portfolio
                WHERE user_email = :email
            """), {"email": user_email}).fetchall()

        profile_dict["plan"] = user.plan if user else "FREE"

        portfolio_list = [dict(p._mapping) for p in portfolio]

        from intelligence.user_intelligence_engine import compute_user_intelligence

        result = compute_user_intelligence(user_email)

        return {
            "user": user_email,
            "intelligence": result
        }

    return safe_execute(_run, module_name="USER_INTELLIGENCE_PIPELINE")
