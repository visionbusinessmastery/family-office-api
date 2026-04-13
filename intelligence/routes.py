import logging
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from .schemas import GlobalQuery
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
def global_intelligence(data: GlobalRequest):
    try:
        result = global_ai_service(data)
        return result

    except Exception as e:
        logging.error(f"GLOBAL AI ERROR: {str(e)}")
        return {
            "status": "error",
            "message": "Erreur dans l'intelligence globale",
            "details": str(e)
        }
