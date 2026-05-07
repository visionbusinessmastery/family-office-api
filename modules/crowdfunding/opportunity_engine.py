# =========================
# OPPORTUNITY ENGINE CROWDFUNDING
# =========================
def get_crowdfunding_opportunities(user_profile):

    score = user_profile.get("score", 0)

    opportunities = []

    if score < 50:

        opportunities.append({
            "title": "Crowdfunding immobilier",
            "platform": "Bricks",
            "risk": "medium",
            "potential": "medium",
            "type": "crowdfunding"
        })

    else:

        opportunities.append({
            "title": "Private Equity participatif",
            "platform": "Fundora",
            "risk": "high",
            "potential": "high",
            "type": "crowdfunding"
        })

    return opportunities
