from fastapi import APIRouter, Request
from core.utils import safe_execute
from .schemas import AdvisorRequest
from .service import advisor_logic

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
