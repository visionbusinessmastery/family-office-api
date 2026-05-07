# =========================
# OPPORTUNITY ENGINE AI BUSINESS
# =========================
def get_ai_business_opportunities(user_profile):

    level = user_profile.get("level", "FREE")

    opportunities = []

    opportunities.append({
        "title": "Agence IA automatisation",
        "risk": "medium",
        "potential": "high",
        "type": "ai_business"
    })

    if level in ["PLATINUM", "GOLD", "ELITE"]:

        opportunities.append({
            "title": "Micro SaaS IA",
            "risk": "high",
            "potential": "very_high",
            "type": "ai_business"
        })

    return opportunities
