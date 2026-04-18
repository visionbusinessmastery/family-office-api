from fastapi import APIRouter, Request
from core.limiter import limiter
from core.utils import safe_execute
from .service import generate_rebalancing

router = APIRouter()


@router.get("/auto-trade")
@limiter.limit("10/minute")
def auto_trade(request: Request):

    def _trade():
        user_email = request.state.user_email

        result = generate_rebalancing(user_email)

        return {
            "user": user_email,
            "result": result
        }

    return safe_execute(_trade, module_name="AUTO_TRADE")
