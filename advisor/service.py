import os
import json
from openai import OpenAI

from business.service import get_business_intelligence
from portfolio.service import get_user_portfolio
from market.service import get_market

# ⚠️ fonctions manquantes protégées
try:
    from intelligence.service import get_user_intelligence
except:
    def get_user_intelligence(user_email):
        return {}

try:
    from business.service import get_business_opportunities
except:
    def get_business_opportunities(user_email):
        return {}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# CORE ADVISOR ENGINE
# =========================
def advisor_logic(user_email, message, mode="free"):

    intelligence = get_user_intelligence(user_email)
    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    business = None
    if mode in ["premium", "elite"]:
        business = get_business_opportunities(user_email)

    prompt = f"""
Tu es un conseiller financier IA de niveau institutionnel.

=== MODE ===
{mode.upper()}

=== INTELLIGENCE UTILISATEUR ===
{json.dumps(intelligence, indent=2)}

=== PORTFOLIO ===
{portfolio}

=== MARCHÉ ===
{market}
"""

    if business:
        prompt += f"\n=== OPPORTUNITÉS BUSINESS ===\n{business}\n"

    prompt += f"""
=== DEMANDE UTILISATEUR ===
{message}

Donne une réponse :
- stratégique
- actionnable
- allocation claire
- décisions concrètes
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "mode": mode,
        "intelligence": intelligence,
        "advice": response.choices[0].message.content
    }


# =========================
# LEVELS (FREE / PREMIUM / ELITE)
# =========================

def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, mode="free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, mode="premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, mode="elite")
