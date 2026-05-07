# =========================
# OPPORTUNITY ENGINE STOCKS
# =========================
def get_stock_opportunities(user_profile):

    score = user_profile.get("score", 0)

    risk = user_profile.get("risk_profile", "medium")

    opportunities = []

    # =========================
    # LOW SCORE USERS
    # =========================
    if score < 40:

        opportunities.append({
            "title": "ETF diversifiés long terme",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "stocks"
        })

        opportunities.append({
            "title": "Portefeuille passif 3 ETF",
            "difficulty": "easy",
            "budget": "low",
            "potential": "medium",
            "type": "stocks"
        })

    # =========================
    # ADVANCED USERS
    # =========================
    else:

        if risk == "low":

            opportunities.append({
                "title": "Dividend Aristocrats Portfolio",
                "difficulty": "medium",
                "budget": "medium",
                "potential": "stable",
                "type": "stocks"
            })

        elif risk == "medium":

            opportunities.append({
                "title": "Growth + Value Strategy",
                "difficulty": "advanced",
                "budget": "medium",
                "potential": "high",
                "type": "stocks"
            })

        else:

            opportunities.append({
                "title": "High Volatility Tech Portfolio",
                "difficulty": "advanced",
                "budget": "high",
                "potential": "very_high",
                "type": "stocks"
            })

    return opportunities
