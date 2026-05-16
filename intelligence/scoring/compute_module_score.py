# =========================
# MODULE SCORE WRAPPER
# =========================

from intelligence.scoring.scoring_registry import SCORING_ENGINES

def compute_module_score(module_name: str, context: dict):

    engine = SCORING_ENGINES.get(module_name)

    if not engine:
        return {
            "score": 0,
            "module": module_name,
            "error": "Unknown module"
        }

    try:
        score = engine(context)

        return {
            "score": score,
            "module": module_name
        }

    except Exception as e:
        return {
            "score": 0,
            "module": module_name,
            "error": str(e)
        }
