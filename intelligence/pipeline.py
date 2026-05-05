# =========================
# intelligence/pipeline.py
# SIMPLIFIÉ - SAFE WRAPPER (PRODUCTION READY)
# =========================

from intelligence.user_intelligence_engine import get_user_intelligence


# =========================
# MAIN WRAPPER (LEGACY SAFE)
# =========================
def run_user_intelligence(user_email, profile=None, portfolio=None, conn=None):
    """
    Wrapper compatible legacy.
    Ne casse pas les anciennes routes même si signature évolue.
    """

    try:
        if not user_email:
            return {
                "error": "missing_user_email",
                "score": {"score": 0},
                "level": "FREE"
            }

        # =========================
        # MAIN CALL
        # =========================
        result = get_user_intelligence(user_email)

        # =========================
        # SAFE FALLBACKS (ANTI-CRASH FRONT)
        # =========================
        if not isinstance(result, dict):
            return {
                "error": "invalid_intelligence_response",
                "score": {"score": 0},
                "level": "FREE"
            }

        result.setdefault("score", {"score": 0})
        result.setdefault("level", "FREE")
        result.setdefault("features", [])
        result.setdefault("opportunities", [])
        result.setdefault("upgrade", None)

        return result

    except Exception as e:
        return {
            "error": str(e),
            "score": {"score": 0},
            "level": "FREE",
            "features": [],
            "opportunities": [],
            "upgrade": None
        }
