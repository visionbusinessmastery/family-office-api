def compute_family_office_score(profile: dict, portfolio: list):
    """
    Family Office Scoring Engine
    - Wealth Score
    - Diversification Score
    - Risk Alignment
    - Activity Score
    - Global Score
    - Level + Advice
    """

    # =========================
    # SAFE VALUES
    # =========================
    savings = profile.get("savings") or 0
    investments = profile.get("investments") or 0
    risk_profile = (profile.get("risk_profile") or "medium").lower()

    total_assets = savings + investments

    # =========================
    # 1. WEALTH SCORE (0-100)
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
    # 2. DIVERSIFICATION SCORE
    # =========================
    asset_types = set()

    for asset in portfolio or []:
        if asset and asset.get("type"):
            asset_types.add(asset.get("type"))

    diversification = min(len(asset_types) * 25, 100)

    # =========================
    # 3. RISK ALIGNMENT
    # =========================
    crypto_exposure = 0
    total_value = 0

    for asset in portfolio or []:
        if not asset:
            continue

        value = asset.get("value") or 0
        total_value += value

        if asset.get("type") == "crypto":
            crypto_exposure += value

    crypto_ratio = crypto_exposure / total_value if total_value > 0 else 0

    risk_score = 100

    if risk_profile == "low":
        if crypto_ratio > 0.2:
            risk_score = 40
        elif crypto_ratio > 0.1:
            risk_score = 60

    elif risk_profile == "medium":
        if crypto_ratio > 0.4:
            risk_score = 60
        elif crypto_ratio > 0.6:
            risk_score = 40

    elif risk_profile == "high":
        risk_score = 80

    # =========================
    # 4. ACTIVITY SCORE
    # =========================
    activity = 100 if profile else 30

    # =========================
    # 5. GLOBAL SCORE (WEIGHTED)
    # =========================
    score = int(
        (wealth * 0.35) +
        (diversification * 0.25) +
        (risk_score * 0.25) +
        (activity * 0.15)
    )

    # clamp 0-100
    score = max(0, min(score, 100))

    # =========================
    # 6. LEVEL (PROFILE STAGE READY)
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
    # 7. RECOMMENDATIONS
    # =========================
    advice = []

    if diversification < 50:
        advice.append("Diversifie tes actifs (immobilier, actions, business, crypto)")

    if risk_score < 60:
        advice.append("Rééquilibre ton exposition au risque")

    if wealth < 50:
        advice.append("Augmente ton capital investi et ton épargne")

    if crypto_ratio > 0.5 and risk_profile == "low":
        advice.append("Réduis ton exposition crypto (trop risqué pour ton profil)")

    if total_assets < 10000:
        advice.append("Concentre-toi sur l'accumulation de capital")

    # =========================
    # 8. RETURN FINAL OBJECT
    # =========================
    return {
        "score": score,
        "level": level,
        "details": {
            "wealth": wealth,
            "diversification": diversification,
            "risk": risk_score,
            "activity": activity,
            "crypto_ratio": round(crypto_ratio, 3)
        },
        "advice": advice
    }
