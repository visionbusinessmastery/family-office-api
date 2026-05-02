from business.service import get_business_intelligence
from portfolio.service import get_user_portfolio
from market.service import get_market
from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# CORE ADVISOR ENGINE
# =========================
def advisor_logic(user_email: str, message: str, mode: str = "free"):

    # 1. DATA LAYER (stable sources)
    intelligence = get_business_intelligence(user_email)
    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    # ELITE ONLY ADDITION (placeholder safe)
    business_opportunities = intelligence.get("opportunities", {}) if isinstance(intelligence, dict) else {}

    # 2. MODE CONFIG
    if mode == "free":
        context_limit = "basic"
    elif mode == "premium":
        context_limit = "extended"
    else:
        context_limit = "full institutional"

    # 3. PROMPT ENGINE
    prompt = f"""
Tu es un conseiller financier IA de niveau institutionnel.

MODE ACTUEL : {mode.upper()} ({context_limit})

=== INTELLIGENCE UTILISATEUR ===
{json.dumps(intelligence, indent=2)}

=== PORTFOLIO ===
{portfolio}

=== MARCHÉ ===
{market}

=== OPPORTUNITÉS BUSINESS ===
{json.dumps(business_opportunities, indent=2)}

=== DEMANDE UTILISATEUR ===
{message}

INSTRUCTIONS :
- donne une stratégie claire
- propose allocation si pertinent
- sois actionnable immédiatement
- adapte le niveau de profondeur au mode
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
# TIERS LOGIC
# =========================
def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, mode="free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, mode="premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, mode="elite")
