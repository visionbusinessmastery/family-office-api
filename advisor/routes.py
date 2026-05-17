# =========================
# ADVISOR ROUTES V4 CLEAN
# =========================

from fastapi import APIRouter, Request
from core.utils import safe_execute
from core.limiter import limiter

from .schemas import AdvisorRequest

from .service import (
    get_advisor_free,
    portfolio_autopilot,
    portfolio_manager,
)

router = APIRouter()


# =========================
# 1. CHAT ADVISOR (IA CONSEIL)
# =========================
@router.post("/advisor")
@limiter.limit("10/minute")
def advisor(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email

        result = get_advisor_free(user_email, data.message)

        return {
            "user": user_email,
            "system": "ADVISOR_CHAT_V4",
            "tier": "free",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="ADVISOR_CHAT")


# =========================
# 2. PORTFOLIO ANALYSIS (READ ONLY)
# =========================
@router.post("/advisor/portfolio")
@limiter.limit("10/minute")
def advisor_portfolio(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email

        result = portfolio_manager(user_email, data.message)

        return {
            "user": user_email,
            "system": "PORTFOLIO_ANALYSIS_V4",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="PORTFOLIO_MANAGER")


# =========================
# 3. AUTOPILOT ENGINE (SIMULATION / DECISION)
# =========================
@router.post("/advisor/autopilot")
@limiter.limit("10/minute")
def advisor_autopilot(request: Request, data: AdvisorRequest):

    def _run():
        user_email = request.state.user_email

        result = portfolio_autopilot(user_email, data.message)

        return {
            "user": user_email,
            "system": "AUTOPILOT_ENGINE_V4",
            "mode": "SIMULATION",
            "input": data.message,
            "result": result
        }

    return safe_execute(_run, module_name="AUTOPILOT_ENGINE")
