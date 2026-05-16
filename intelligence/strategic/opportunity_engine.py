# =========================
# OPPORTUNITY ENGINE V2
# =========================

import json
import hashlib

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
# HASH BUILDER
# =========================
def build_hash(profile, portfolio):

    raw = json.dumps({
        "profile": profile,
        "portfolio": portfolio
    }, sort_keys=True)

    return hashlib.md5(
        raw.encode()
    ).hexdigest()


# =========================
# SAFE FLOAT
# =========================
def safe_float(value):

    try:
        return float(value or 0)
    except:
        return 0


# =========================
# MAIN ENGINE
# =========================
def compute_opportunities(
    profile: dict,
    portfolio: list
):

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(portfolio, list):
        portfolio = []

    # =========================
    # CACHE KEY
    # =========================
    cache_hash = build_hash(
        profile,
        portfolio
    )

    cache_key = (
        f"opportunities:"
        f"{cache_hash}"
    )

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)

    if cached:
        return cached

    opportunities = []

    # =========================
    # PROFILE DATA
    # =========================
    risk = (
        profile.get("risk_profile")
        or "medium"
    ).lower().strip()

    savings = safe_float(
        profile.get("savings")
    )

    investments = safe_float(
        profile.get("investments")
    )

    plan = (
        profile.get("plan")
        or "FREE"
    ).upper()

    total_assets = (
        savings + investments
    )

    # =========================
    # PORTFOLIO ANALYTICS
    # =========================
    asset_types = set()

    crypto_exposure = 0

    stock_exposure = 0

    total_portfolio = 0

    for asset in portfolio:

        if not isinstance(asset, dict):
            continue

        asset_type = (
            asset.get("type")
            or ""
        ).lower()

        value = safe_float(
            asset.get("value")
        )

        total_portfolio += value

        if asset_type:
            asset_types.add(asset_type)

        if asset_type == "crypto":
            crypto_exposure += value

        elif asset_type in [
            "stocks",
            "stock",
            "equity"
        ]:
            stock_exposure += value

    crypto_ratio = (
        crypto_exposure / total_portfolio
        if total_portfolio > 0 else 0
    )

    # =========================
    # REAL ESTATE
    # =========================
    if savings >= 20000:

        priority = (
            "high"
            if savings >= 50000
            else "medium"
        )

        opportunities.append({

            "type":
                "real_estate",

            "title":
                "Opportunité immobilière",

            "description":
                "Investissement locatif potentiel détecté",

            "priority":
                priority,

            "score":
                85 if priority == "high"
                else 65,

            "premium":
                False,
        })

    # =========================
    # CRYPTO
    # =========================
    if risk in ["medium", "high"]:

        crypto_priority = (
            "high"
            if risk == "high"
            else "medium"
        )

        opportunities.append({

            "type":
                "crypto",

            "title":
                "Signal crypto marché",

            "description":
                "Exposition crypto optimisable",

            "priority":
                crypto_priority,

            "score":
                90 if risk == "high"
                else 70,

            "premium":
                False,
        })

    # =========================
    # BUSINESS
    # =========================
    if (
        savings >= 10000
        or total_assets >= 15000
    ):

        opportunities.append({

            "type":
                "business",

            "title":
                "Business scalable détecté",

            "description":
                "Business digital fortement recommandé",

            "priority":
                "medium",

            "score":
                75,

            "premium":
                False,
        })

    # =========================
    # DIVERSIFICATION
    # =========================
    if len(asset_types) <= 2:

        opportunities.append({

            "type":
                "diversification",

            "title":
                "Diversification portefeuille",

            "description":
                "Portefeuille insuffisamment diversifié",

            "priority":
                "high",

            "score":
                88,

            "premium":
                False,
        })

    # =========================
    # PREMIUM AI SIGNALS
    # =========================
    if plan in [
        "PRO",
        "ELITE",
        "LIBERTY"
    ]:

        if crypto_ratio > 0.60:

            opportunities.append({

                "type":
                    "ai_rebalance",

                "title":
                    "AI Portfolio Rebalancing",

                "description":
                    "Concentration crypto excessive détectée",

                "priority":
                    "high",

                "score":
                    95,

                "premium":
                    True,
            })

        if total_assets >= 100000:

            opportunities.append({

                "type":
                    "private_equity",

                "title":
                    "Private Equity Access",

                "description":
                    "Eligible à des investissements privés",

                "priority":
                    "high",

                "score":
                    92,

                "premium":
                    True,
            })

    # =========================
    # REMOVE DUPLICATES
    # =========================
    unique = {}

    for opp in opportunities:

        unique[
            opp["type"]
        ] = opp

    opportunities = list(
        unique.values()
    )

    # =========================
    # SORTING
    # =========================
    opportunities.sort(
        key=lambda x: x.get(
            "score",
            0
        ),
        reverse=True
    )

    # =========================
    # FINAL PAYLOAD
    # =========================
    result = {

        "count":
            len(opportunities),

        "opportunities":
            opportunities,

        "analytics": {

            "crypto_ratio":
                round(
                    crypto_ratio,
                    4
                ),

            "asset_types_count":
                len(asset_types),

            "portfolio_value":
                round(
                    total_portfolio,
                    2
                ),
        }
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
