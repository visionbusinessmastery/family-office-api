# =========================
# IMPORTS
# =========================
import json
from core.cache import redis_client

from intelligence.engines.risk_engine import compute_risk_profile
from intelligence.engines.wealth_engine import compute_wealth_projection
from intelligence.engines.allocation_engine import compute_allocation_strategy
from intelligence.engines.diversification_engine import compute_diversification
from intelligence.engines.prediction_engine import compute_predictions
from intelligence.engines.macro_engine import compute_macro_exposure
from intelligence.engines.recommendation_engine import generate_recommendations


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
# SAFE ENGINE WRAPPER
# =========================
def safe_run(engine_fn, context, name):
    try:
        return engine_fn(context)
    except Exception:
        return {"error": f"{name}_failed"}


# =========================
# STRATEGIC LAYER (OPTIMIZED)
# =========================
def compute_strategic_layer(
    profile=None,
    portfolio=None,
    score=0,
    financial=None,
    version="v1"
):

    profile = profile or {}
    portfolio = portfolio or []
    financial = financial or {}

    # =========================
    # CACHE KEY (IMPORTANT)
    # =========================
    cache_key = f"strategic:{version}:{profile.get('email','unknown')}:{score}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # CONTEXT BUILD
    # =========================
    context = {
        "profile": profile,
        "portfolio": portfolio,
        "score": score,
        "financial": financial,
    }

    # =========================
    # AI ENGINES (ISOLATED)
    # =========================
    risk = safe_run(compute_risk_profile, context, "risk")
    wealth = safe_run(compute_wealth_projection, context, "wealth")
    allocation = safe_run(compute_allocation_strategy, context, "allocation")
    diversification = safe_run(compute_diversification, context, "diversification")
    prediction = safe_run(compute_predictions, context, "prediction")
    macro = safe_run(compute_macro_exposure, context, "macro")

    # =========================
    # RECOMMENDATION ENGINE
    # =========================
    recommendations = safe_run(
        lambda ctx: generate_recommendations(
            context=ctx,
            risk=risk,
            wealth=wealth,
            allocation=allocation,
            diversification=diversification,
            prediction=prediction,
            macro=macro,
        ),
        context,
        "recommendations"
    )

    # =========================
    # FINAL PAYLOAD
    # =========================
    result = {
        "version": version,

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
