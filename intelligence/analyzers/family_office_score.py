# =========================
# COMPUTE FAMILY OFFICE
# =========================
def compute_family_office_score(profile: dict, portfolio: list, financial: dict = None):

    savings = profile.get("savings") or 0
    investments = profile.get("investments") or 0
    risk_profile = (profile.get("risk_profile") or "medium").lower()

    total_assets = savings + investments

    # =========================
    # WEALTH SCORE
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
    asset_types = set()

    for asset in portfolio or []:
        if asset.get("type"):
            asset_types.add(asset["type"])

    diversification = min(len(asset_types) * 25, 100)

    # =========================
    # RISK
    # =========================
    crypto = sum(a.get("value", 0) for a in portfolio if a.get("type") == "crypto")
    total_value = sum(a.get("value", 0) for a in portfolio)

    crypto_ratio = crypto / total_value if total_value > 0 else 0

    risk_score = 100

    if risk_profile == "low":
        risk_score = 40 if crypto_ratio > 0.2 else 60 if crypto_ratio > 0.1 else 80

    elif risk_profile == "medium":
        risk_score = 40 if crypto_ratio > 0.6 else 60 if crypto_ratio > 0.4 else 80

    # =========================
    # ACTIVITY
    # =========================
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
    # FINAL SCORE
    # =========================
    score = int(
        (wealth * 0.25) +
        (diversification * 0.20) +
        (risk_score * 0.20) +
        (activity * 0.10) +
        (financial_score * 0.25)
    )

    score = max(0, min(score, 100))

    # =========================
    # LEVEL
    # =========================
    level = "ELITE" if score >= 85 else "ADVANCED" if score >= 70 else "INTERMEDIATE" if score >= 50 else "BEGINNER"

    # =========================
    # ADVICE
    # =========================
    advice = []

    if diversification < 50:
        advice.append("Diversifie tes actifs")

    if financial and financial.get("debt_risk_score", 0) > 60:
        advice.append("Réduis ton niveau d'endettement")

    if financial and financial.get("cashflow_score", 0) < 0:
        advice.append("Améliore ton cashflow")

    return {
        "score": score,
        "level": level,
        "details": {
            "wealth": wealth,
            "diversification": diversification,
            "risk": risk_score,
            "activity": activity,
            "financial": financial_score
        },
        "advice": advice
    }
