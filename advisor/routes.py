from fastapi import APIRouter, Request
from core.utils import safe_execute
from core.limiter import limiter

from .schemas import AdvisorRequest, AdvisorPremiumRequest
from .service import advisor_logic, get_advisor_premium, get_advisor_auto

from pydantic import BaseModel


router = APIRouter()

@router.post("/advisor")
def advisor(request: Request, data: AdvisorRequest):

    def _advisor():
        user_email = request.state.user_email

        result = advisor_logic(data.message)

        return {
            "user": user_email,
            "input": data.message,
            "result": result
        }

    return safe_execute(_advisor, module_name="ADVISOR")

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


@router.post("/advisor/auto")
@limiter.limit("10/minute")
def advisor_auto(request: Request):

    def _auto():
        user_email = request.state.user_email

        result = get_advisor_auto(user_email)

        return {
            "user": user_email,
            "result": result
        }

    return safe_execute(_auto, module_name="ADVISOR_AUTO")
