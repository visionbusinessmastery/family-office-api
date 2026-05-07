# =========================
# OPPORTUNITY ENGINE WEALTH
# =========================
def get_wealth_opportunities(user_profile):

    opportunities = []

    capital = user_profile.get("capital", 0)

    if capital < 10000:

        opportunities.append({
            "title": "Construction fonds de sécurité",
            "priority": "high",
            "type": "wealth"
        })

    else:

        opportunities.append({
            "title": "Diversification patrimoniale",
            "priority": "high",
            "type": "wealth"
        })

    opportunities.append({
        "title": "Plan liberté financière 10 ans",
        "priority": "high",
        "type": "wealth"
    })

    return opportunities
