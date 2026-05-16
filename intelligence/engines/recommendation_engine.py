# =========================
# AI RECOMMENDATION ENGINE
# =========================

def generate_recommendations(context: dict):

    recommendations = []

    income = context.get(
        "monthly_income",
        0
    )

    savings = context.get(
        "savings",
        0
    )

    if savings < 5000:

        recommendations.append(
            "Construire une épargne de sécurité"
        )

    if income < 3000:

        recommendations.append(
            "Développer des revenus complémentaires"
        )

    if context.get("crypto_ratio", 0) > 0.5:

        recommendations.append(
            "Réduire la concentration crypto"
        )

    return recommendations
