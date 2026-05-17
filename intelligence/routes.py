# =========================
# INTELLIGENCE ROUTES V4 CLEAN
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Request
from core.limiter import limiter
from core.utils import safe_execute

from .schemas import GlobalRequest

from .service import (
    get_global_intelligence,
    get_family_office_score
)

from intelligence.user_intelligence_engine import compute_user_intelligence

router = APIRouter()


# =========================
# GLOBAL INTELLIGENCE
# =========================
@router.post("/global")
@limiter.limit("5/minute")
def global_intelligence(request: Request, data: GlobalRequest):

    def _run():
        user_email = request.state.user_email

        result = get_global_intelligence(data)

        return {
            "user": user_email,
            "query": data.dict(),
            "result": result
        }

    return safe_execute(_run, module_name="GLOBAL_INTELLIGENCE")


# =========================
# FAMILY OFFICE SCORE
# =========================
@router.get("/family-office-score")
def family_office_score(request: Request):

    def _run():
        user_email = request.state.user_email

        result = get_family_office_score(user_email)

        return {
            "user": user_email,
            "family_office_index": result
        }

    return safe_execute(_run, module_name="FAMILY_OFFICE_SCORE")


# =========================
# USER INTELLIGENCE (CORE AI SYSTEM)
# =========================
@router.get("/user-intelligence")
def user_intelligence(request: Request):

    def _run():
        user_email = request.state.user_email
        return compute_user_intelligence(user_email)

    return safe_execute(_run, module_name="USER_INTELLIGENCE")


# =========================
# PIPELINE ENTRY POINT
# =========================
@router.get("/run")
def run_intelligence(request: Request):

    def _run():
        user_email = request.state.user_email

        result = compute_user_intelligence(user_email)

        return {
            "user": user_email,
            "intelligence": result,
            "system": "V4_INTELLIGENCE_ENGINE"
        }

    return safe_execute(_run, module_name="USER_INTELLIGENCE_PIPELINE")


# =========================
# FRONTEND PAYLOAD NORMALIZER
# =========================
def build_command_center_payload(user_email: str):
    intelligence = compute_user_intelligence(user_email)
    family_score = intelligence.get("family_office_score") or intelligence.get("score") or {}
    details = family_score.get("details", {})

    return {
        "user": intelligence.get("user", user_email),
        "plan": intelligence.get("plan", "FREE"),
        "global_score": intelligence.get("global_score", family_score.get("score", 0)),
        "level": intelligence.get("level", family_score.get("level", "BEGINNER")),
        "onboarding": intelligence.get("onboarding", {}),
        "family_office_score": {
            "score": family_score.get("score", 0),
            "level": family_score.get("level", intelligence.get("level", "BEGINNER")),
            "details": {
                "wealth": details.get("wealth", 0),
                "diversification": details.get("diversification", 0),
                "debt": details.get("debt", 0),
                "activity": details.get("activity", 0),
                "financial_score": details.get("financial_score", 0),
                "crypto_ratio": details.get("crypto_ratio", 0),
            },
            "advice": family_score.get("advice", []),
        },
        "gamification": intelligence.get("gamification", {}),
        "modules": intelligence.get("modules", {}),
        "advice": intelligence.get("advice", []),
        "strategic_intelligence": intelligence.get("strategic_intelligence", {}),
    }


# =========================
# GLOBAL COMMAND CENTER
# =========================
@router.get("/global-command-center")
def global_command_center(request: Request):

    def _run():
        return build_command_center_payload(request.state.user_email)
        
    return safe_execute(
        _run,
        module_name="GLOBAL_COMMAND_CENTER"
    )
