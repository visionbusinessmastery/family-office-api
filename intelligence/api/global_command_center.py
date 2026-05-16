# =========================
# GLOBAL COMMAND CENTER FIXED
# =========================

import logging
from fastapi import APIRouter

from intelligence.scoring.compute_module_score import compute_module_score
from intelligence.scoring.scoring_context_builder import build_scoring_context

from intelligence.engines.risk_engine import compute_risk_profile
from intelligence.engines.wealth_engine import compute_wealth_projection
from intelligence.engines.allocation_engine import compute_allocation_strategy
from intelligence.engines.diversification_engine import compute_diversification
from intelligence.engines.prediction_engine import compute_predictions
from intelligence.engines.macro_engine import compute_macro_exposure
from intelligence.engines.recommendation_engine import generate_recommendations

from intelligence.strategic.strategic_layer import compute_strategic_layer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/global-command-center", tags=["Global Command Center"])


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


def compute_global_command_center(user=None, onboarding=None, portfolio=None, financial_overview=None):

    onboarding = onboarding or {}
    portfolio = portfolio or []
    financial_overview = financial_overview or {}

    try:

        context = build_scoring_context(
            user=user,
            onboarding=onboarding,
            portfolio=portfolio,
            financial_overview=financial_overview,
        )

        modules = {}
        weighted_total = 0
        total_weight = 0

        for name, weight in MODULE_WEIGHTS.items():

            result = compute_module_score(name, context)
            score = result.get("score", 0)

            modules[name] = {"score": score, "weight": weight}

            weighted_total += score * weight
            total_weight += weight

        global_score = int(weighted_total / total_weight) if total_weight else 0
        global_score = max(0, min(global_score, 100))

        level = compute_level(global_score)

        advice = []

        if modules.get("crypto", {}).get("score", 0) < 40:
            advice.append("Développe tes connaissances crypto")

        if modules.get("real_estate", {}).get("score", 0) < 50:
            advice.append("Augmente ton exposition immobilière")

        if modules.get("business", {}).get("score", 0) < 50:
            advice.append("Développe des revenus business")

        return {
            "global_score": global_score,
            "level": level,
            "modules": modules,
            "advice": advice,
            "context": context
        }

    except Exception as e:
        logger.error(f"GLOBAL COMMAND ERROR: {e}")

        return {
            "global_score": 0,
            "level": "BEGINNER",
            "modules": {},
            "advice": [],
            "error": str(e)
        }
