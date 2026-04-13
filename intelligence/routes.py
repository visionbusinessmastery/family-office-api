import logging
from fastapi import APIRouter, Depends, HTTPException
from core.utils import safe_execute

from .schemas import GlobalQuery   # ✅ cohérent
from .service import get_global_intelligence  # ✅ cohérent

router = APIRouter()

@router.post("/global")
def global_intelligence(data: GlobalQuery):
    return safe_execute(
        get_global_intelligence,
        data,
        "GLOBAL INTELLIGENCE"
    )
    
