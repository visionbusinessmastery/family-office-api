# =========================
# GLOBAL FINANCIAL COMMAND CENTER V2
# =========================

import logging

from intelligence.scoring.compute_module_score import (
    compute_module_score
)

from intelligence.scoring.scoring_context_builder import (
    build_scoring_context
)

logger = logging.getLogger(__name__)


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
        # MODULE SCORES
        # =========================
        modules = {}

        weighted_total = 0
        total_weight = 0

        for module_name, weight in MODULE_WEIGHTS.items():

            result = compute_module_score(
                module_name,
                context
            )

            module_score = result.get("score", 0)

            modules[module_name] = {
                "score": module_score,
                "weight": weight,
            }

            weighted_total += module_score * weight
            total_weight += weight

        # =========================
        # GLOBAL SCORE
        # =========================
        global_score = int(
            weighted_total / total_weight
        ) if total_weight > 0 else 0

        global_score = max(
            0,
            min(global_score, 100)
        )

        # =========================
        # LEVEL
        # =========================
        level = compute_level(global_score)

        # =========================
        # AI ADVICE
        # =========================
        advice = []

        if modules["crypto"]["score"] < 40:
            advice.append(
                "Développe tes connaissances crypto"
            )

        if modules["real_estate"]["score"] < 50:
            advice.append(
                "Augmente ton exposition immobilière"
            )

        if modules["business"]["score"] < 50:
            advice.append(
                "Développe des revenus business"
            )

        if modules["banking"]["score"] < 50:
            advice.append(
                "Renforce ton épargne de sécurité"
            )

        if modules["entrepreneurship"]["score"] > 80:
            advice.append(
                "Excellent potentiel entrepreneurial"
            )

        # =========================
        # FINAL PAYLOAD
        # =========================
        return {

            "global_score": global_score,

            "level": level,

            "modules": modules,

            "advice": advice,

            "context": {

                "monthly_income": context.get(
                    "monthly_income",
                    0
                ),

                "savings": context.get(
                    "savings",
                    0
                ),

                "capital": context.get(
                    "capital",
                    0
                ),

                "risk_profile": context.get(
                    "risk_profile"
                ),

                "portfolio_value": context.get(
                    "portfolio_value",
                    0
                ),
            }
        }

    except Exception as e:

        logger.error(
            f"[GLOBAL COMMAND CENTER ERROR] {e}"
        )

        return {

            "global_score": 0,

            "level": "BEGINNER",

            "modules": {},

            "advice": [],

            "error": str(e),
        }
