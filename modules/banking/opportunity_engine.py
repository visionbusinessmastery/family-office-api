# =========================
# OPPORTUNITY ENGINE BANKING
# =========================
def get_banking_opportunities(user_profile):

    capital = user_profile.get("capital", 0)

    opportunities = []

    opportunities.append({
        "title": "Compte rémunéré haute liquidité",
        "risk": "low",
        "potential": "low",
        "type": "banking"
    })

    if capital > 10000:

        opportunities.append({
            "title": "Optimisation crédit stratégique",
            "risk": "medium",
            "potential": "medium",
            "type": "banking"
        })

    return opportunities
