from fastapi import APIRouter, Request
from core.utils import safe_execute
from core.limiter import limiter

from .schemas import (
    AdvisorRequest,
    AdvisorPremiumRequest,
    AdvisorEliteRequest
)

from .service import (
    get_advisor_free,
    get_advisor_premium,
    get_advisor_elite
)


from .service import portfolio_manager

router = APIRouter()

# =========================
# FREE
# =========================
@router.post("/advisor")
@limiter.limit("10/minute")
def advisor(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email

        result = get_advisor_free(user_email, data.message)

        return {
            "user": user_email,
            "tier": "free",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="ADVISOR_FREE")


# =========================
# PREMIUM
# =========================
@router.post("/advisor/premium")
@limiter.limit("10/minute")
def advisor_premium(request: Request, data: AdvisorPremiumRequest):

    def _run():
        user_email = request.state.user_email

        result = get_advisor_premium(user_email, data.message)

        return {
            "user": user_email,
            "tier": "premium",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="ADVISOR_PREMIUM")


# =========================
# ELITE (HEDGE FUND MODE)
# =========================
@router.post("/advisor/elite")
@limiter.limit("10/minute")
def advisor_elite(request: Request, data: AdvisorEliteRequest):

    def _run():
        user_email = request.state.user_email

        result = get_advisor_elite(user_email, data.message)

        return {
            "user": user_email,
            "tier": "elite",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="ADVISOR_ELITE")


@router.post("/portfolio/manager")
@limiter.limit("10/minute")
def portfolio_ai(request: Request, data: dict):

    def _run():
        user_email = request.state.user_email

        result = portfolio_manager(user_email, data["message"])

        return {
            "user": user_email,
            "system": "AI_PORTFOLIO_MANAGER_V6",
            "input": data["message"],
            "result": result
        }

    return safe_execute(_run, module_name="PORTFOLIO_AI")


@router.post("/portfolio/autopilot")
@limiter.limit("10/minute")
def autopilot(request: Request, data: dict):

    def _run():
        user_email = request.state.user_email

        result = portfolio_autopilot(user_email, data["message"])

        return {
            "user": user_email,
            "system": "AI_AUTOPILOT_V7",
            "result": result
        }

    return safe_execute(_run, module_name="AUTOPILOT")


