# =========================
# OPPORTUNITY ENGINE BUSINESS
# =========================
def get_business_opportunities(user_profile):

    score = user_profile.get("score", 0)

    opportunities = []

    # =========================
    # LOW LEVEL USERS
    # =========================
    if score < 40:

        opportunities.append({
            "title": "Micro-agence IA",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "business"
        })

        opportunities.append({
            "title": "UGC Creator Business",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "business"
        })

    # =========================
    # ADVANCED USERS
    # =========================
    else:

        opportunities.append({
            "title": "Acquisition PME",
            "difficulty": "advanced",
            "budget": "high",
            "potential": "high",
            "type": "business"
        })

    return opportunities
