# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from auth.utils import get_current_user

# 🔥 MOTEUR CENTRAL UNIQUE (source de vérité)
from intelligence.user_intelligence_engine import compute_user_intelligence

router = APIRouter()


# =========================
# RECALCULATE SCORE
# =========================
@router.post("/score/recalculate")
def recalculate_score(user=Depends(get_current_user)):

    email = user

    try:
        # =========================
        # ENGINE CALL
        # =========================
        intel = compute_user_intelligence(email)

        if not intel:
            return {
                "error": "Impossible de recalculer",
                "score": 0,
                "details": {},
                "advice": [],
                "level": "UNKNOWN"
            }

        score_data = intel.get("score", {}) or {}

        return {
            "score": score_data.get("score", 0),
            "details": score_data.get("details", {}),
            "advice": score_data.get("advice", []),
            "level": intel.get("level", "UNKNOWN"),
            "plan": intel.get("plan", {})
        }

    except Exception as e:
        return {
            "error": "Score engine failure",
            "message": str(e),
            "score": 0,
            "details": {},
            "advice": [],
            "level": "UNKNOWN"
        }
