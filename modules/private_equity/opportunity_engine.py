# =========================
# OPPORTUNITY ENGINE PRIVATE EQUITY
# =========================
def get_private_equity_opportunities(user_profile):

    capital = user_profile.get("capital", 0)

    opportunities = []

    if capital > 100000:

        opportunities.append({
            "title": "Acquisition PME rentable",
            "risk": "medium",
            "potential": "very_high",
            "type": "private_equity"
        })

    return opportunities
