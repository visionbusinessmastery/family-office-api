import os
import json
from openai import OpenAI

from business.service import get_business_intelligence
from portfolio.service import get_user_portfolio
from market.service import get_market

from advisor.engine import detect_risk, detect_goal, extract_budget, build_allocation

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# CORE ADVISOR ENGINE
# =========================
def build_advisor_context(user_email: str, message: str):

    return {
        "intelligence": {},  # placeholder si tu ajoutes user intelligence
        "portfolio": get_user_portfolio(user_email),
        "market": get_market("global"),
        "business": get_business_intelligence(user_email),
        "budget": extract_budget(message),
        "risk": detect_risk(message),
        "goal": detect_goal(message),
        "allocation": build_allocation(detect_risk(message))
    }


def run_llm(context, message):

    prompt = f"""
Tu es un conseiller financier IA niveau hedge fund.

=== CONTEXTE ===
{json.dumps(context, indent=2)}

=== DEMANDE ===
{message}

Règles:
- Donne une stratégie claire
- Allocation concrète
- Actions immédiates
- Risques expliqués simplement
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


def advisor_logic(user_email: str, message: str):

    context = build_advisor_context(user_email, message)
    advice = run_llm(context, message)

    return {
        "context": context,
        "advice": advice
    }


# =========================
# TIERS SYSTEM (IMPORTANT)
# =========================

def get_advisor_free(user_email, message):
    context = build_advisor_context(user_email, message)
    context["market"] = None  # downgrade

    return {
        "tier": "FREE",
        "data": advisor_logic(user_email, message)
    }


def get_advisor_premium(user_email, message):
    return {
        "tier": "PREMIUM",
        "data": advisor_logic(user_email, message)
    }


def get_advisor_elite(user_email, message):
    context = build_advisor_context(user_email, message)

    # ELITE = full context + extra reasoning
    context["advanced_mode"] = True

    return {
        "tier": "ELITE",
        "data": {
            **advisor_logic(user_email, message),
            "alpha_signals": "enabled",
            "strategy_depth": "institutional"
        }
    }
