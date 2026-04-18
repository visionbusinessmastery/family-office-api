from fastapi import APIRouter, Request
from core.utils import safe_execute
from core.limiter import limiter

from .schemas import FranchiseRequest
from .service import get_franchise_advisor

router = APIRouter()


@router.post("/franchise")
@limiter.limit("10/minute")
def franchise(request: Request, data: FranchiseRequest):

    def _franchise():

        user_email = request.state.user_email

        result = get_franchise_advisor(data)

        return {
            "user": user_email,
            "input": data.dict(),
            "result": result
        }

    return safe_execute(_franchise, module_name="FRANCHISE")
