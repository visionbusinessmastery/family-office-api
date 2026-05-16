# intelligence/strategic/strategic_layer.py

# =========================
# IMPORTS
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
def compute_strategic_layer(
    profile=None,
    portfolio=None,
    score=0,
    financial=None
):

    profile = profile or {}
    portfolio = portfolio or []
    financial = financial or {}

    # =========================
    # BUILD CONTEXT
    # =========================
    context = {
        "profile": profile,
        "portfolio": portfolio,
        "score": score,
        "financial": financial,
    }

    # =========================
    # AI ENGINES
    # =========================
    risk = compute_risk_profile(context)

    wealth = compute_wealth_projection(context)

    allocation = compute_allocation_strategy(context)

    diversification = compute_diversification(context)

    prediction = compute_predictions(context)

    macro = compute_macro_exposure(context)

    recommendations = generate_recommendations(
        context=context,
        risk=risk,
        wealth=wealth,
        allocation=allocation,
        diversification=diversification,
        prediction=prediction,
        macro=macro,
    )

    # =========================
    # FINAL PAYLOAD
    # =========================
    return {

        "risk_engine": risk,

        "wealth_engine": wealth,

        "allocation_engine": allocation,

        "diversification_engine": diversification,

        "prediction_engine": prediction,

        "macro_engine": macro,

        "recommendations": recommendations,
    }
