# =========================
# AI RECOMMENDATION ENGINE
# =========================

def generate_recommendations(
    context: dict,
    risk=None,
    wealth=None,
    allocation=None,
    diversification=None,
    prediction=None,
    macro=None,
):

    recommendations = []

    # =========================
    # SAFE CONTEXT
    # =========================
    profile = context.get("profile", {}) or {}
    financial = context.get("financial", {}) or {}

    income = (
        profile.get("monthly_income")
        or financial.get("cashflow_score")
        or 0
    )

    savings = (
        profile.get("epargne")
        or profile.get("savings")
        or 0
    )

    crypto_ratio = (
        financial.get("crypto_ratio")
        or 0
    )

    risk_score = (
        (risk or {}).get("risk_score", 50)
    )

    diversification_score = (
        (diversification or {}).get(
            "diversification_score",
            50
        )
    )

    # =========================
    # SAVINGS
    # =========================
    if savings < 5000:

        recommendations.append(
            "Construire une épargne de sécurité"
        )

    # =========================
    # INCOME
    # =========================
    if income < 3000:

        recommendations.append(
            "Développer des revenus complémentaires"
        )

    # =========================
    # CRYPTO EXPOSURE
    # =========================
    if crypto_ratio > 0.5:

        recommendations.append(
            "Réduire la concentration crypto"
        )

    # =========================
    # RISK
    # =========================
    if risk_score > 75:

        recommendations.append(
            "Réduire le niveau de risque global"
        )

    # =========================
    # DIVERSIFICATION
    # =========================
    if diversification_score < 40:

        recommendations.append(
            "Diversifier davantage les actifs"
        )

    # =========================
    # EMPTY STATE
    # =========================
    if not recommendations:

        recommendations.append(
            "Structure financière équilibrée"
        )

    return recommendations
