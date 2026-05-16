# =========================
# GLOBAL FINANCIAL COMMAND CENTER V3
# =========================

import logging

from fastapi import APIRouter

from intelligence.scoring.compute_module_score import (
    compute_module_score
)

from intelligence.scoring.scoring_context_builder import (
    build_scoring_context
)

# =========================
# AI ENGINES
# =========================
from intelligence.engines.risk_engine import (
    compute_risk_profile
)

from intelligence.engines.wealth_engine import (
    compute_wealth_projection
)

from intelligence.engines.allocation_engine import (
    compute_allocation_strategy
)

from intelligence.engines.diversification_engine import (
    compute_diversification
)

from intelligence.engines.prediction_engine import (
    compute_predictions
)

from intelligence.engines.macro_engine import (
    compute_macro_exposure
)

from intelligence.engines.recommendation_engine import (
    generate_recommendations
)

# =========================
# STRATEGIC LAYER
# =========================
from intelligence.strategic.strategic_layer import (
    compute_strategic_layer
)

logger = logging.getLogger(__name__)

# =========================
# FASTAPI ROUTER
# =========================
router = APIRouter(
    prefix="/global-command-center",
    tags=["Global Command Center"]
)

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
    user=None,
    onboarding=None,
    portfolio=None,
    financial_overview=None,
):

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
        # MODULE SCORING
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
        # AI ENGINES
        # =========================
        risk_engine = compute_risk_profile(context)

        wealth_engine = compute_wealth_projection(context)

        allocation_engine = compute_allocation_strategy(
            context
        )

        diversification_engine = (
            compute_diversification(
                context
            )
        )

        prediction_engine = compute_predictions(
            context
        )

        macro_engine = compute_macro_exposure(
            context
        )

        recommendations = (
            generate_recommendations(
                context
            )
        )

        # =========================
        # STRATEGIC INTELLIGENCE
        # =========================
        strategic_intelligence = (
            compute_strategic_layer(
                context=context,
                modules=modules,
                risk_engine=risk_engine,
                wealth_engine=wealth_engine,
                allocation_engine=allocation_engine,
                diversification_engine=diversification_engine,
                prediction_engine=prediction_engine,
                macro_engine=macro_engine,
            )
        )

        # =========================
        # AI ADVICE
        # =========================
        advice = []

        if risk_engine.get("risk_level") == "HIGH":
            advice.append(
                "Réduire l’exposition aux actifs volatils"
            )

        if wealth_engine.get("wealth_level") == "LOW":
            advice.append(
                "Augmenter les revenus et l’épargne"
            )

        if diversification_engine.get(
            "diversification_score",
            0
        ) < 40:
            advice.append(
                "Diversifier davantage le portefeuille"
            )

        # =========================
        # FINAL PAYLOAD
        # =========================
        return {

            "global_score": global_score,
            "level": level,

            "modules": modules,

            "risk_engine": risk_engine,

            "wealth_engine": wealth_engine,

            "allocation_engine": allocation_engine,

            "diversification_engine":
                diversification_engine,

            "prediction_engine":
                prediction_engine,

            "macro_engine":
                macro_engine,

            "recommendations":
                recommendations,

            "strategic_intelligence":
                strategic_intelligence,

            "advice": advice,

            "context": {

                "monthly_income":
                    context.get(
                        "monthly_income",
                        0
                    ),

                "savings":
                    context.get(
                        "savings",
                        0
                    ),

                "capital":
                    context.get(
                        "capital",
                        0
                    ),

                "risk_profile":
                    context.get(
                        "risk_profile"
                    ),

                "portfolio_value":
                    context.get(
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

            "risk_engine": {},

            "wealth_engine": {},

            "allocation_engine": {},

            "diversification_engine": {},

            "prediction_engine": {},

            "macro_engine": {},

            "recommendations": [],

            "strategic_intelligence": {},

            "advice": [],

            "error": str(e),
        }


# =========================
# API ROUTE
# =========================
@router.get("/")
def global_command_center_health():

    return {
        "status": "Global Command Center Online"
    }


@router.get("/demo")
def global_command_center_demo():

    return compute_global_command_center()
