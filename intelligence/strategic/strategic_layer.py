# strategic/strategic_layer.py

from intelligence.engines.risk_engine import compute_risk_profile
from intelligence.engines.wealth_engine import compute_wealth_projection
from intelligence.engines.allocation_engine import compute_allocation_strategy
from intelligence.engines.diversification_engine import compute_diversification
from intelligence.engines.prediction_engine import compute_predictions
from intelligence.engines.macro_engine import compute_macro_exposure
from intelligence.engines.recommendation_engine import compute_recommendations


def compute_strategic_layer(context: dict, modules: dict):

    risk = compute_risk_engine(context, modules)
    wealth = compute_wealth_engine(context, modules)
    allocation = compute_allocation_engine(context, modules)
    diversification = compute_diversification_engine(context, modules)
    prediction = compute_prediction_engine(context, modules)
    macro = compute_macro_engine(context, modules)

    recommendations = compute_recommendations(
        risk=risk,
        wealth=wealth,
        allocation=allocation,
        macro=macro,
        modules=modules
    )

    return {
        "risk_engine": risk,
        "wealth_engine": wealth,
        "allocation_engine": allocation,
        "diversification_engine": diversification,
        "prediction_engine": prediction,
        "macro_engine": macro,
        "recommendations": recommendations
    }
