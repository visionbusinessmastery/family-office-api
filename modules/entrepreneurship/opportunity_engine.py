# =========================
# OPPORTUNITY ENGINE ENTREPRENEURSHIP
# =========================
def get_entrepreneurship_opportunities(user_profile):

    opportunities = []

    level = user_profile.get("level", "free")

    opportunities.append({
        "title": "Business digital automatisé",
        "difficulty": "medium",
        "type": "entrepreneurship"
    })

    opportunities.append({
        "title": "Side business IA",
        "difficulty": "medium",
        "type": "entrepreneurship"
    })

    if level in ["gold", "elite"]:

        opportunities.append({
            "title": "Acquisition entreprise rentable",
            "difficulty": "high",
            "type": "entrepreneurship"
        })

    return opportunities
