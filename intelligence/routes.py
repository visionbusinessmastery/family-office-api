import logging
from core.utils import safe_execute
from fastapi import APIRouter, Depends, HTTPException
from intelligence.schemas import GlobalRequest
from .service import get_global_intelligence

router = APIRouter()

@router.post("/global")
def global_intelligence(data: GlobalRequest):
    return safe_execute(global_intelligence_service, data, "GLOBAL INTELLIGENCE")

    except Exception as e:
        logging.error(f"GLOBAL AI ERROR: {str(e)}")
        return {
            "status": "error",
            "message": "Erreur dans l'intelligence globale",
            "details": str(e)
        }
