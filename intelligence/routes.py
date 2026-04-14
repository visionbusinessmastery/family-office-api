from fastapi import APIRouter
from core.utils import safe_execute

from .schemas import GlobalRequest   # ✅ corrigé
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
def global_intelligence(data: GlobalRequest):   # ✅ corrigé
    return safe_execute(
        get_global_intelligence,
        data,
        "GLOBAL_INTELLIGENCE"
    )
