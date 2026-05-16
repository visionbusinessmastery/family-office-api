# =========================
# MODULE SCORE WRAPPER (PREMIUM)
# =========================

import time
import json

from intelligence.scoring.scoring_registry import (
    SCORING_ENGINES
)

from core.cache import redis_client


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):

    try:

        if redis_client:

            data = redis_client.get(key)

            if data:
                return json.loads(data)

    except:
        pass

    return None


def set_cache(key, value, ttl=300):

    try:

        if redis_client:

            redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )

    except:
        pass


# =========================
# MODULE SCORE ENGINE
# =========================
def compute_module_score(
    module_name: str,
    context: dict
):

    # =========================
    # CACHE KEY
    # =========================
    cache_key = (
        f"module_score:{module_name}:"
        f"{hash(str(context))}"
    )

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)

    if cached:
        return cached

    # =========================
    # ENGINE FETCH
    # =========================
    engine = SCORING_ENGINES.get(module_name)

    if not engine:

        result = {
            "score": 0,
            "module": module_name,
            "error": "Unknown module"
        }

        return result

    # =========================
    # ENGINE EXECUTION
    # =========================
    started = time.time()

    try:

        raw_score = engine(context)

        # =========================
        # SAFE SCORE
        # =========================
        if isinstance(raw_score, dict):

            score = raw_score.get("score", 0)

        else:

            score = raw_score

        score = max(
            0,
            min(int(score or 0), 100)
        )

        execution_time = round(
            time.time() - started,
            4
        )

        result = {

            "score": score,

            "module": module_name,

            "execution_time":
                execution_time,

            "cached": False,
        }

        # =========================
        # CACHE STORE
        # =========================
        set_cache(
            cache_key,
            result,
            ttl=300
        )

        return result

    except Exception as e:

        return {

            "score": 0,

            "module": module_name,

            "error": str(e),

            "cached": False,
        }
