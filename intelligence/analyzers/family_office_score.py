# =========================
# COMPUTE FAMILY OFFICE
import logging

logger = logging.getLogger(__name__)


# =========================
# SAFE GETTER
# =========================
def safe_get(d, key, default=0):
    try:
        return d.get(key, default) if isinstance(d, dict) else default
    except Exception:
        return default


# =========================
# MAIN ENGINE
# =========================
def compute_family_office_score(profile: dict, portfolio: list, financial: dict = None):

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
        # 1. WEALTH SCORE
        # =========================
        if total_assets >= 100000:
            wealth = 90
        elif total_assets >= 50000:
            wealth = 70
        elif total_assets >= 10000:
            wealth = 50
        elif total_assets > 0:
            wealth = 30
        else:
            wealth = 10

        # =========================
        # 2. DIVERSIFICATION
        # =========================
        asset_types = set()

        for asset in portfolio or []:
           if isinstance(asset, dict):
               t = (asset.get("type") or "").lower()
               if t:
                   asset_types.add(t)
    
        diversification = min(len(asset_types) * 25, 100)

        # =========================
        # 3. RISK ALIGNMENT
        # =========================
        crypto_exposure = 0
        total_value = 0

        for asset in portfolio or []:
            if not isinstance(asset, dict):
                continue

            value = safe_get(asset, "value", 0)
            total_value += value

            if (asset.get("type") or "").lower() == "crypto":
                crypto_exposure += value

        crypto_ratio = crypto_exposure / total_value if total_value > 0 else 0

        risk_score = 70  # default SAFE baseline

        if risk_profile == "low":
            risk_score = 100 if crypto_ratio <= 0.1 else 60
        elif risk_profile == "medium":
            risk_score = 80 if crypto_ratio <= 0.4 else 50
        elif risk_profile == "high":
            risk_score = 85

        # =========================
        # 4. ACTIVITY SCORE
        # =========================
        activity = 100 if profile else 30

        # =========================
        # 5. FINANCIAL SCORE (SAFE)
        # =========================
        financial_score = 50  # fallback intelligent default

        try:
            if financial:

                cashflow = safe_get(financial, "cashflow_score", 0)
                debt_risk = safe_get(financial, "debt_risk_score", 50)
                savings_velocity = safe_get(financial, "savings_velocity_score", 0)
                income_stability = safe_get(financial, "income_stability_score", 0)

                financial_score = (
                    cashflow * 0.4 +
                    (100 - debt_risk) * 0.3 +
                    savings_velocity * 0.2 +
                    income_stability * 0.1
                )

        except Exception as e:
            logger.warning(f"[FINANCIAL SCORE ERROR] {e}")

        # =========================
        # 6. GLOBAL SCORE
        # =========================
        score = int(
            (wealth * 0.25) +
            (diversification * 0.20) +
            (risk_score * 0.15) +
            (activity * 0.10) +
            (financial_score * 0.30)
        )

        # SAFE CLAMP
        score = max(5, min(score, 100))  # 🔥 NEVER 0

        # =========================
        # 7. LEVEL
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
        # 8. ADVICE ENGINE
        # =========================
        advice = []

        if diversification < 50:
            advice.append("Diversifie tes actifs")

        if risk_score < 60:
            advice.append("Rééquilibre ton risque")

        if wealth < 50:
            advice.append("Augmente ton capital")

        if financial_score < 40:
            advice.append("Améliore ton cashflow")

        # =========================
        # 9. DEBUG PAYLOAD (IMPORTANT)
        # =========================
        debug = {
            "wealth": wealth,
            "diversification": diversification,
            "risk_score": risk_score,
            "activity": activity,
            "financial_score": round(financial_score, 2),
            "crypto_ratio": round(crypto_ratio, 3)
        }

        # =========================
        # RETURN
        # =========================
        return {
            "score": score,
            "level": level,
            "details": debug,
            "advice": advice
        }

    except Exception as e:
        logger.error(f"[FAMILY OFFICE SCORE CRASH] {e}")

        return {
            "score": 10,
            "level": "BEGINNER",
            "details": {},
            "advice": ["Erreur de calcul, données incomplètes"]
        }
