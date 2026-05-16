# =========================
# GLOBAL FINANCIAL COMMAND CENTER V2 (OPTIMIZED)
# =========================

import logging
import json

from intelligence.scoring.compute_module_score import compute_module_score
from intelligence.scoring.scoring_context_builder import build_scoring_context
from core.cache import redis_client

logger = logging.getLogger(__name__)


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
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# MODULE WEIGHTS
# =========================
MODULE_WEIGHTS = {
    "business": 1.2,
    "crypto": 0.9,
    "real_estate": 1.3,
    "banking": 1.0,
    "market": 1.0,
    "stocks": 1.1,
    "startup": 0.8,
    "private_equity": 1.4,
    "franchise": 0.9,
    "etf": 1.1,
    "entrepreneurship": 1.2,
    "crowdfunding": 0.6,
    "commodities": 0.8,
    "ai_business": 1.0,
}


# =========================
# LEVEL ENGINE
# =========================
def compute_level(score: int):

    if score >= 90:
        return "LEGEND"
    if score >= 80:
        return "ELITE"
    if score >= 70:
        return "ADVANCED"
    if score >= 50:
        return "INTERMEDIATE"
    return "BEGINNER"


# =========================
# SAFE GET
# =========================
def safe_get(d, key, default=0):
    try:
        return d.get(key, default) if isinstance(d, dict) else default
    except:
        return default


# =========================
# MAIN ENGINE
# =========================
def compute_global_command_center(
    user,
    onboarding=None,
    portfolio=None,
    financial_overview=None,
):

    onboarding = onboarding or {}
    portfolio = portfolio or []
    financial_overview = financial_overview or {}

    # =========================
    # CACHE KEY
    # =========================
    cache_key = f"cmd_center:{user.id}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    try:

        # =========================
        # BUILD CONTEXT
        # =========================
        context = build_scoring_context(
            user=user,
            onboarding=onboarding,
            portfolio=portfolio,
            financial_overview=financial_overview,
        )

        # =========================
        # MODULES
        # =========================
        modules = {}
        weighted_total = 0
        total_weight = 0

        for module_name, weight in MODULE_WEIGHTS.items():

            result = compute_module_score(module_name, context) or {}

            module_score = safe_get(result, "score", 0)

            modules[module_name] = {
                "score": module_score,
                "weight": weight,
            }

            weighted_total += module_score * weight
            total_weight += weight

        # =========================
        # GLOBAL SCORE
        # =========================
        global_score = int(weighted_total / total_weight) if total_weight > 0 else 0
        global_score = max(0, min(global_score, 100))

        # =========================
        # LEVEL
        # =========================
        level = compute_level(global_score)

        # =========================
        # SAFE MODULE ACCESS
        # =========================
        def m(name):
            return modules.get(name, {}).get("score", 0)

        # =========================
        # ADVICE ENGINE
        # =========================
        advice = []

        if m("crypto") < 40:
            advice.append("Développe tes connaissances crypto")

        if m("real_estate") < 50:
            advice.append("Augmente ton exposition immobilière")

        if m("business") < 50:
            advice.append("Développe des revenus business")

        if m("banking") < 50:
            advice.append("Renforce ton épargne de sécurité")

        if m("entrepreneurship") > 80:
            advice.append("Excellent potentiel entrepreneurial")

        # =========================
        # RESULT
        # =========================
        result = {
            "global_score": global_score,
            "level": level,
            "modules": modules,
            "advice": advice
        }

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result

    except Exception as e:

        logger.error(f"[GLOBAL COMMAND CENTER ERROR] {e}")

        return {
            "global_score": 0,
            "level": "BEGINNER",
            "modules": {},
            "advice": [],
            "error": str(e),
        }
