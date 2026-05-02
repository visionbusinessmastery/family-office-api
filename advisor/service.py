
from business.service import get_business_opportunities
from portfolio.service import get_user_portfolio
from market.service import get_market
from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# =========================
# ADVISOR = ORCHESTRATOR ONLY
# =========================
def advisor_logic(user_email, message):

    # 1. SINGLE SOURCE OF TRUTH
    intelligence = get_user_intelligence(user_email)
    portfolio = get_user_portfolio(user_email)
    market = get_market("global")
    business = get_business_opportunities(user_email)

    # 2. CLEAN PROMPT
    prompt = f"""
    Tu es un conseiller financier IA de niveau institutionnel.

    === INTELLIGENCE UTILISATEUR ===
    {json.dumps(intelligence, indent=2)}

    === PORTFOLIO ===
    {portfolio}

    === MARCHÉ ===
    {market}

    === OPPORTUNITÉS BUSINESS ===
    {business}

    === DEMANDE UTILISATEUR ===
    {message}

    Donne une réponse :
    - stratégique
    - actionnable
    - orientée allocation + décisions concrètes
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "intelligence": intelligence,
        "advice": response.choices[0].message.content
    }
