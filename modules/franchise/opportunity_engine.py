# =========================
# OPPORTUNITY ENGINE FRANCHISE
# =========================
def get_franchise_opportunities(user_profile):

    budget = user_profile.get("capital", 0)

    opportunities = []

    if budget < 50000:

        opportunities.append({
            "title": "Micro franchise digitale",
            "risk": "medium",
            "potential": "medium",
            "type": "franchise"
        })

    else:

        opportunities.append({
            "title": "Franchise restauration",
            "risk": "high",
            "potential": "high",
            "type": "franchise"
        })

    return opportunities
