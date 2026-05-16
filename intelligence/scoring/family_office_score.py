import logging
from core.cache import redis_client
import json

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
# SAFE GETTER
# =========================
def safe_get(d, key, default=0):
    try:
        return d.get(key, default) if isinstance(d, dict) else default
    except:
        return default


# =========================
# MAIN ENGINE (OPTIMIZED)
# =========================
def compute_family_office_score(profile: dict, portfolio: list, financial: dict = None):

    cache_key = f"score:{profile.get('email','unknown')}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    financial = financial or {}

    try:
        # =========================
        # SAFE VALUES
        # =========================
        savings = safe_get(profile, "savings", 0)
        investments = safe_get(profile, "investments", 0)
        risk_profile = (safe_get(profile, "risk_profile", "medium") or "medium").lower()

        total_assets = savings + investments

        # =========================
        # WEALTH SCORE (SMOOTHED)
        # =========================
        wealth = min(100, (total_assets / 100000) * 100)

        # =========================
        # DIVERSIFICATION
        # =========================
        asset_types = set()

        for asset in (portfolio or []):
            if isinstance(asset, dict):
                t = (asset.get("type") or "").lower()
                if t:
                    asset_types.add(t)

        diversification = min(len(asset_types) * 20, 100)

        # =========================
        # RISK EXPOSURE
        # =========================
        crypto_exposure = 0
        total_value = 0

        for asset in (portfolio or []):
            if not isinstance(asset, dict):
                continue

            value = safe_get(asset, "value", 0)
            total_value += value

            if (asset.get("type") or "").lower() == "crypto":
                crypto_exposure += value

        crypto_ratio = crypto_exposure / total_value if total_value > 0 else 0

        # =========================
        # RISK SCORE (COHERENT)
        # =========================
        if risk_profile == "low":
            risk_score = 100 if crypto_ratio <= 0.1 else 50
        elif risk_profile == "medium":
            risk_score = 80 if crypto_ratio <= 0.3 else 40
        else:
            risk_score = 70

        # =========================
        # ACTIVITY SCORE (REAL SIGNAL)
        # =========================
        activity = min(100, len(profile.keys()) * 10)

        # =========================
        # FINANCIAL SCORE (NORMALIZED)
        # =========================
        financial_score = 50

        if financial:
            cashflow = safe_get(financial, "cashflow_score", 0)
            debt_risk = safe_get(financial, "debt_risk_score", 50)
            savings_velocity = safe_get(financial, "savings_velocity_score", 0)
            income_stability = safe_get(financial, "income_stability_score", 0)

            financial_score = (
                min(max(cashflow, 0), 100) * 0.4 +
                (100 - min(max(debt_risk, 0), 100)) * 0.3 +
                min(max(savings_velocity, 0), 100) * 0.2 +
                min(max(income_stability, 0), 100) * 0.1
            )

        # =========================
        # GLOBAL SCORE
        # =========================
        score = int(
            (wealth * 0.30) +
            (diversification * 0.20) +
            (risk_score * 0.15) +
            (activity * 0.10) +
            (financial_score * 0.25)
        )

        score = max(5, min(score, 100))

        # =========================
        # LEVEL
        # =========================
        if score >= 85:
            level = "ELITE"
        elif score >= 70:
            level = "ADVANCED"
        elif score >= 50:
            level = "INTERMEDIATE"
        else:
            level = "BEGINNER"

        # =========================
        # ADVICE ENGINE
        # =========================
        advice = []

        if diversification < 40:
            advice.append("Diversifie tes actifs")

        if risk_score < 60:
            advice.append("Rééquilibre ton risque")

        if wealth < 40:
            advice.append("Augmente ton patrimoine")

        if financial_score < 40:
            advice.append("Améliore ton cashflow")

        # =========================
        # DEBUG
        # =========================
        result = {
            "score": score,
            "level": level,
            "details": {
                "wealth": round(wealth, 2),
                "diversification": diversification,
                "risk_score": risk_score,
                "activity": activity,
                "financial_score": round(financial_score, 2),
                "crypto_ratio": round(crypto_ratio, 3),
            },
            "advice": advice,
        }

        # =========================
        # CACHE STORE
        # =========================
        set_cache(cache_key, result, ttl=300)

        return result

    except Exception as e:
        logger.error(f"[FAMILY OFFICE SCORE CRASH] {e}")

        return {
            "score": 10,
            "level": "BEGINNER",
            "details": {},
            "advice": ["Erreur de calcul"]
        }
