from product.entitlements import plan_allows


def get_ai_business_opportunities(user_profile):

    level = user_profile.get("level") or user_profile.get("plan") or "FREE"

    opportunities = []

    opportunities.append({
        "title": "Agence automatisation",
        "risk": "medium",
        "potential": "high",
        "type": "ai_business"
    })

    if plan_allows(level, "GOLD"):

        opportunities.append({
            "title": "Micro SaaS automatisation",
            "risk": "high",
            "potential": "very_high",
            "type": "ai_business"
        })

    return opportunities
