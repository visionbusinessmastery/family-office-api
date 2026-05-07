# =========================
# OPPORTUNITY ENGINE CRYPTO
# =========================
def get_crypto_opportunities(user_profile):

    risk_profile = user_profile.get("risk_profile", "medium")

    opportunities = []

    if risk_profile == "high":

        opportunities.append({
            "title": "AI Crypto Narratives",
            "risk": "high",
            "potential": "high",
            "type": "crypto"
        })

    else:

        opportunities.append({
            "title": "Bitcoin DCA",
            "risk": "medium",
            "potential": "medium",
            "type": "crypto"
        })

    return opportunities
