def compute_family_office_score(profile: dict, portfolio: list):

    # =========================
    # 1. WEALTH SCORE (0-100)
    # =========================
    wealth = 0
    total_assets = (profile.get("savings", 0) or 0) + (profile.get("investments", 0) or 0)

    if total_assets > 100000:
        wealth = 90
    elif total_assets > 50000:
        wealth = 70
    elif total_assets > 10000:
        wealth = 50
    else:
        wealth = 20

    # =========================
    # 2. DIVERSIFICATION SCORE
    # =========================
    asset_types = set()

    for asset in portfolio:
        asset_types.add(asset.get("type"))

    diversification = min(len(asset_types) * 25, 100)

    # =========================
    # 3. RISK ALIGNMENT
    # =========================
    risk_profile = (profile.get("risk_profile") or "medium").lower()

    crypto_exposure = 0
    total_value = 0

    for asset in portfolio:
        value = asset.get("value", 0)
        total_value += value

        if asset.get("type") == "crypto":
            crypto_exposure += value

    crypto_ratio = (crypto_exposure / total_value) if total_value > 0 else 0

    risk_score = 100

    if risk_profile == "low" and crypto_ratio > 0.2:
        risk_score = 40
    elif risk_profile == "medium" and crypto_ratio > 0.4:
        risk_score = 60

    # =========================
    # 4. ACTIVITY SCORE
    # =========================
    activity = 100 if profile else 30

    # =========================
    # GLOBAL SCORE
    # =========================
    score = int(
        (wealth * 0.3) +
        (diversification * 0.3) +
        (risk_score * 0.2) +
        (activity * 0.2)
    )

    # =========================
    # LEVEL
    # =========================
    if score > 80:
        level = "Elite"
    elif score > 60:
        level = "Advanced"
    elif score > 40:
        level = "Intermediate"
    else:
        level = "Beginner"

    # =========================
    # RECOMMENDATIONS
    # =========================
    advice = []

    if diversification < 50:
        advice.append("Diversifie tes actifs (immo, actions, business)")

    if risk_score < 60:
        advice.append("Rééquilibre ton exposition au risque")

    if wealth < 50:
        advice.append("Augmente ta capacité d’investissement")

    return {
        "score": score,
        "level": level,
        "details": {
            "wealth": wealth,
            "diversification": diversification,
            "risk": risk_score,
            "activity": activity
        },
        "advice": advice
    }
