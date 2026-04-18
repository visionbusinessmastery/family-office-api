from fastapi import APIRouter, Request
from core.limiter import limiter
from core.utils import safe_execute
from .service import generate_alerts

router = APIRouter()


@router.get("/alerts")
@limiter.limit("20/minute")
def alerts(request: Request):

    def _alerts():
        user_email = request.state.user_email

        result = generate_alerts(user_email)

        return {
            "user": user_email,
            "result": result
        }

    return safe_execute(_alerts, module_name="ALERTS")
