import logging
import json

from core.cache import redis_client

logger = logging.getLogger(__name__)


# =========================================================
# CACHE HELPERS
# =========================================================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)

            if data:
                return json.loads(data)

    except Exception as e:
        logger.error(f"[CACHE GET ERROR] {e}")

    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )

    except Exception as e:
        logger.error(f"[CACHE SET ERROR] {e}")


# =========================================================
# SAFE GETTER
# =========================================================
def safe_get(d, key, default=0):
    try:
        if isinstance(d, dict):
            return d.get(key, default)

    except:
        pass

    return default


# =========================================================
# SAFE NUMBER
# =========================================================
def safe_number(value, default=0):
    try:
        return float(value)

    except:
        return default


# =========================================================
# MAIN ENGINE
# =========================================================
def compute_family_office_score(
    profile: dict,
    portfolio: list,
    financial: dict = None
):

    financial = financial or {}

    cache_key = f"score:{profile.get('email', 'unknown')}"

    # =====================================================
    # CACHE CHECK
    # =====================================================
    cached = get_cache(cache_key)

    if cached:
        return cached

    try:

        # =====================================================
        # PROFILE
        # =====================================================
        risk_profile = (
            safe_get(profile, "risk_profile", "medium") or "medium"
        ).lower()

        # =====================================================
        # PORTFOLIO VALUE
        # =====================================================
        portfolio_value = 0

        asset_types = set()

        crypto_exposure = 0

        for asset in (portfolio or []):

            if not isinstance(asset, dict):
                continue

            asset_value = safe_number(
                safe_get(asset, "value", 0)
            )

            portfolio_value += asset_value

            asset_type = (
                safe_get(asset, "type", "") or ""
            ).lower()

            if asset_type:
                asset_types.add(asset_type)

            if asset_type == "crypto":
                crypto_exposure += asset_value

        # =====================================================
        # FINANCIAL DATA
        # =====================================================
        epargne = financial.get("epargne", [])
        revenus = financial.get("revenus", [])
        charges = financial.get("charges", [])
        dettes = financial.get("dettes", [])

        # =====================================================
        # SAVINGS
        # =====================================================
        savings_total = sum(
            safe_number(item.get("amount", 0))
            for item in epargne
            if isinstance(item, dict)
        )

        # =====================================================
        # DEBT
        # =====================================================
        total_debt = sum(
            safe_number(item.get("amount", 0))
            for item in dettes
            if isinstance(item, dict)
        )

        # =====================================================
        # INCOME
        # =====================================================
        total_income = sum(
            safe_number(item.get("amount", 0))
            for item in revenus
            if isinstance(item, dict)
        )

        # =====================================================
        # EXPENSES
        # =====================================================
        total_expenses = sum(
            safe_number(item.get("amount", 0))
            for item in charges
            if isinstance(item, dict)
        )

        # =====================================================
        # NET WORTH
        # =====================================================
        total_assets = portfolio_value + savings_total

        net_worth = total_assets - total_debt

        # =====================================================
        # WEALTH SCORE
        # =====================================================
        wealth = min(
            100,
            max(0, (net_worth / 100000) * 100)
        )

        # =====================================================
        # DIVERSIFICATION SCORE
        # =====================================================
        diversification = min(
            len(asset_types) * 20,
            100
        )

        # =====================================================
        # CRYPTO RATIO
        # =====================================================
        crypto_ratio = (
            crypto_exposure / portfolio_value
            if portfolio_value > 0
            else 0
        )

        # =====================================================
        # RISK SCORE
        # =====================================================
        if risk_profile == "low":

            risk_score = (
                100 if crypto_ratio <= 0.10 else 50
            )

        elif risk_profile == "medium":

            risk_score = (
                80 if crypto_ratio <= 0.30 else 40
            )

        else:
            risk_score = 70

        # =====================================================
        # DEBT SCORE
        # =====================================================
        debt_ratio = (
            total_debt / total_assets
            if total_assets > 0
            else 1
        )

        debt_score = max(
            0,
            min(100, 100 - (debt_ratio * 100))
        )

        # =====================================================
        # CASHFLOW
        # =====================================================
        cashflow = total_income - total_expenses

        cashflow_score = max(
            0,
            min(100, (cashflow / 5000) * 100)
        )

        # =====================================================
        # SAVINGS VELOCITY
        # =====================================================
        savings_velocity = (
            savings_total / total_income
            if total_income > 0
            else 0
        )

        savings_velocity_score = max(
            0,
            min(100, savings_velocity * 100)
        )

        # =====================================================
        # INCOME STABILITY
        # =====================================================
        income_stability_score = (
            80 if total_income > 0 else 20
        )

        # =====================================================
        # FINANCIAL SCORE
        # =====================================================
        financial_score = (
            cashflow_score * 0.4 +
            debt_score * 0.3 +
            savings_velocity_score * 0.2 +
            income_stability_score * 0.1
        )

        # =====================================================
        # ACTIVITY SCORE
        # =====================================================
        activity = min(
            100,
            (
                len(portfolio) * 10 +
                len(revenus) * 5 +
                len(epargne) * 5
            )
        )

        # =====================================================
        # GLOBAL SCORE
        # =====================================================
        score = int(
            (wealth * 0.30) +
            (diversification * 0.20) +
            (risk_score * 0.15) +
            (activity * 0.10) +
            (debt_score * 0.15) +
            (financial_score * 0.10)
        )

        score = max(5, min(score, 100))

        # =====================================================
        # LEVEL
        # =====================================================
        if score >= 85:
            level = "ELITE"

        elif score >= 70:
            level = "ADVANCED"

        elif score >= 50:
            level = "INTERMEDIATE"

        else:
            level = "BEGINNER"

        # =====================================================
        # ADVICE ENGINE
        # =====================================================
        advice = []

        if diversification < 40:
            advice.append(
                "Diversifie davantage tes actifs"
            )

        if debt_score < 50:
            advice.append(
                "Réduis ton niveau d'endettement"
            )

        if wealth < 40:
            advice.append(
                "Augmente ton patrimoine net"
            )

        if cashflow < 0:
            advice.append(
                "Ton cashflow est négatif"
            )

        if savings_velocity_score < 20:
            advice.append(
                "Augmente ton taux d'épargne"
            )

        if risk_score < 60:
            advice.append(
                "Rééquilibre ton exposition au risque"
            )

        # =====================================================
        # RESULT
        # =====================================================
        result = {

            "score": score,

            "level": level,

            "details": {

                "wealth": round(wealth, 2),

                "diversification": round(
                    diversification,
                    2
                ),

                "debt": round(
                    debt_score,
                    2
                ),

                "risk_score": round(
                    risk_score,
                    2
                ),

                "activity": round(
                    activity,
                    2
                ),

                "financial_score": round(
                    financial_score,
                    2
                ),

                "cashflow_score": round(
                    cashflow_score,
                    2
                ),

                "crypto_ratio": round(
                    crypto_ratio,
                    3
                ),

                "net_worth": round(
                    net_worth,
                    2
                ),

                "portfolio_value": round(
                    portfolio_value,
                    2
                ),

                "total_debt": round(
                    total_debt,
                    2
                ),

                "total_income": round(
                    total_income,
                    2
                ),

                "total_expenses": round(
                    total_expenses,
                    2
                ),

                "savings_total": round(
                    savings_total,
                    2
                ),
            },

            "advice": advice,
        }

        # =====================================================
        # CACHE STORE
        # =====================================================
        set_cache(
            cache_key,
            result,
            ttl=300
        )

        return result

    except Exception as e:

        logger.error(
            f"[FAMILY OFFICE SCORE CRASH] {e}"
        )

        return {
            "score": 10,
            "level": "BEGINNER",
            "details": {},
            "advice": [
                "Erreur de calcul du score"
            ]
        }
