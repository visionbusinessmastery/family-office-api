# =========================
# OPPORTUNITY ENGINE MARKET
# =========================
def get_market_opportunities(user_profile):

    score = user_profile.get("score", 0)

    opportunities = []

    # =========================
    # BEGINNER USERS
    # =========================
    if score < 40:

        opportunities.append({
            "title": "Comprendre les cycles économiques",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "market"
        })

        opportunities.append({
            "title": "Suivi inflation & taux directeurs",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "market"
        })

    # =========================
    # ADVANCED USERS
    # =========================
    else:

        opportunities.append({
            "title": "Stratégie macro multi-actifs",
            "difficulty": "advanced",
            "budget": "medium",
            "potential": "high",
            "type": "market"
        })

        opportunities.append({
            "title": "Détection de cycles économiques avancés",
            "difficulty": "advanced",
            "budget": "medium",
            "potential": "high",
            "type": "market"
        })

    return opportunities
