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


router = APIRouter()

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



from intelligence.user_intelligence_engine import compute_user_intelligence


@router.get("/user-intelligence")
def user_intelligence(request: Request):

    def _engine():
        user_email = request.state.user_email

        result = compute_user_intelligence(user_email)

        return {
            "user": user_email,
            "intelligence": result
        }

    return safe_execute(_engine, module_name="USER_INTELLIGENCE")
