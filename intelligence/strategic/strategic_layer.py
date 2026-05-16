# =========================
# intelligence/strategic/strategic_layer.py
# =========================

# =========================
# IMPORTS
# =========================
from intelligence.engines.risk_engine import compute_risk_profile
from intelligence.engines.wealth_engine import compute_wealth_projection
from intelligence.engines.allocation_engine import compute_allocation_strategy
from intelligence.engines.diversification_engine import compute_diversification
from intelligence.engines.prediction_engine import compute_predictions
from intelligence.engines.macro_engine import compute_macro_exposure
from intelligence.engines.recommendation_engine import generate_recommendations

from core.cache import redis_client
import json


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
# STRATEGIC LAYER (CACHE OPTIMIZED)
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
    # CACHE KEY (GLOBAL STRATEGIC)
    # =========================
    cache_key = f"strategic:{profile.get('email')}:{score}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # BUILD CONTEXT (SINGLE SOURCE OF TRUTH)
    # =========================
    context = {
        "profile": profile,
        "portfolio": portfolio,
        "score": score,
        "financial": financial,
    }

    # =========================
    # ENGINES
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
    result = {
        "risk_engine": risk,
        "wealth_engine": wealth,
        "allocation_engine": allocation,
        "diversification_engine": diversification,
        "prediction_engine": prediction,
        "macro_engine": macro,
        "recommendations": recommendations,
    }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=300)

    return result
