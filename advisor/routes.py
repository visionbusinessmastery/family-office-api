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

router = APIRouter()


# =========================
# FREE
# =========================
@router.post("/advisor")
@limiter.limit("10/minute")
def advisor(request: Request, data: AdvisorRequest):

    def _advisor():
        user_email = request.state.user_email

        result = get_advisor_free(user_email, data.message)

        return {
            "user": user_email,
            "input": data.message,
            "result": result
        }

    return safe_execute(_advisor, module_name="ADVISOR_FREE")


# =========================
# PREMIUM
# =========================
@router.post("/advisor/premium")
@limiter.limit("10/minute")
def advisor_premium(request: Request, data: AdvisorPremiumRequest):

    def _advisor():
        user_email = request.state.user_email

        result = get_advisor_premium(user_email, data.message)

        return {
            "user": user_email,
            "input": data.message,
            "result": result
        }

    return safe_execute(_advisor, module_name="ADVISOR_PREMIUM")


# =========================
# ELITE
# =========================
@router.post("/advisor/elite")
@limiter.limit("10/minute")
def advisor_elite(request: Request, data: AdvisorEliteRequest):

    def _advisor():
        user_email = request.state.user_email

        result = get_advisor_elite(user_email, data.message)

        return {
            "user": user_email,
            "input": data.message,
            "result": result
        }

    return safe_execute(_advisor, module_name="ADVISOR_ELITE")
