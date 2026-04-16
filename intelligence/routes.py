from core.limiter import limiter
from fastapi import APIRouter, Depends, HTTPException, Request
from core.utils import safe_execute

from .schemas import GlobalRequest   # ✅ corrigé
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
@limiter.limit("5/minute")
def global_intelligence(request: Request, data: GlobalRequest):   

    user_email = request.state.user_email
    
    return gobal_intelligence(data)
    
return safe_execute(_global_intelligence, module_name="INTELLIGENCE")
