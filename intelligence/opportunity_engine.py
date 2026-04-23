# =========================
# COMPUTE OPPORTUNITIES
# =========================
def compute_opportunities(profile: dict, portfolio: list):

    opportunities = []

    risk = (profile.get("risk_profile") or "medium").lower()
    savings = profile.get("savings", 0) or 0

    # =========================
    # REAL ESTATE
    # =========================
    if savings > 20000:
        opportunities.append({
            "type": "real_estate",
            "title": "Opportunité immobilière",
            "description": "Investissement locatif rentable détecté",
            "priority": "high"
        })

    # =========================
    # CRYPTO
    # =========================
    if risk in ["medium", "high"]:
        opportunities.append({
            "type": "crypto",
            "title": "Signal crypto",
            "description": "Momentum détecté sur BTC/ETH",
            "priority": "medium"
        })

    # =========================
    # BUSINESS
    # =========================
    if savings > 10000:
        opportunities.append({
            "type": "business",
            "title": "Business scalable",
            "description": "Opportunité de business en ligne détectée",
            "priority": "medium"
        })

    return opportunities
