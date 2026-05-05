# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from auth.utils import get_current_user

# 🔥 MOTEUR CENTRAL UNIQUE
from intelligence.user_intelligence_engine import compute_user_intelligence

router = APIRouter()

# =========================
# RECALCULATE SCORE
# =========================
@router.post("/score/recalculate")
def recalculate_score(user=Depends(get_current_user)):

    user_email = user

    # 🔥 SOURCE UNIQUE DE VÉRITÉ
    intel = compute_user_intelligence(user_email)

    if not intel or "score" not in intel:
        return {"error": "Impossible de recalculer"}

    return {
        "score": intel.get("score", {}).get("score", 0),
        "details": intel.get("score", {}).get("details", {}),
        "advice": intel.get("score", {}).get("advice", []),
        "level": intel.get("level"),
        "plan": intel.get("plan")
    }
