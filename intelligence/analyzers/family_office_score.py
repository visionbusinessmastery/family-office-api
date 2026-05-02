# =========================
# COMPUTE FAMILY OFFICE
# =========================
def compute_family_office_score(profile: dict, portfolio: list, financial: dict = None):

    savings = profile.get("savings") or 0
    investments = profile.get("investments") or 0
    risk_profile = (profile.get("risk_profile") or "medium").lower()

    total_assets = savings + investments

    # =========================
    # WEALTH
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
    # DIVERSIFICATION
    # =========================
    asset_types = {a.get("type") for a in (portfolio or []) if a}

    diversification = min(len(asset_types) * 25, 100)

    # =========================
    # RISK
    # =========================
    crypto = sum(a.get("value", 0) for a in portfolio if a.get("type") == "crypto")
    total_value = sum(a.get("value", 0) for a in portfolio)

    crypto_ratio = crypto / total_value if total_value else 0

    risk_score = 100
    if risk_profile == "low":
        if crypto_ratio > 0.2:
            risk_score = 40
    elif risk_profile == "medium":
        if crypto_ratio > 0.4:
            risk_score = 60

    activity = 100 if profile else 30

    # =========================
    # FINANCIAL SCORE (NEW)
    # =========================
    financial_score = 0

    if financial:
        financial_score = (
            financial.get("cashflow_score", 0) * 0.4 +
            (100 - financial.get("debt_risk_score", 0)) * 0.3 +
            financial.get("savings_velocity_score", 0) * 0.2 +
            financial.get("income_stability_score", 0) * 0.1
        )

    # =========================
    # GLOBAL SCORE
    # =========================
    score = int(
        (wealth * 0.25) +
        (diversification * 0.2) +
        (risk_score * 0.2) +
        (activity * 0.1) +
        (financial_score * 0.25)
    )

    score = max(0, min(score, 100))

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
    # ADVICE
    # =========================
    advice = []

    if diversification < 50:
        advice.append("Diversifie tes actifs")
    if financial and financial.get("debt_risk_score", 0) > 60:
        advice.append("Réduis ton endettement")
    if financial and financial.get("cashflow_score", 0) < 0:
        advice.append("Améliore ton cashflow")

    return {
        "score": score,
        "level": level,
        "details": {
            "wealth": wealth,
            "diversification": diversification,
            "risk": risk_score,
            "financial_score": financial_score,
            "crypto_ratio": round(crypto_ratio, 3)
        },
        "advice": advice
    }
