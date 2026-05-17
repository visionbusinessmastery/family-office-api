# =========================
# INTELLIGENCE ROUTES SCORES
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Depends
from auth.utils import get_current_user

from intelligence.user_intelligence_engine import compute_user_intelligence

router = APIRouter()


# =========================
# RECALCULATE SCORE
# =========================
@router.post("/score/recalculate")
def recalculate_score(user=Depends(get_current_user)):

    email = user  # get_current_user retourne email

    try:
        # =========================
        # ENGINE CALL (SOURCE OF TRUTH)
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

        score_data = intel.get("family_office_score") or intel.get("score", {}) or {}

        return {
            "score": score_data.get("score", 0),
            "details": score_data.get("details", {}),
            "advice": score_data.get("advice", []),
            "level": intel.get("level", "UNKNOWN"),
            "plan": intel.get("plan", "FREE")
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
