import os
import json
from openai import OpenAI

from portfolio.service import get_user_portfolio
from market.service import get_market
from business.service import get_business_intelligence
from advisor.engine import detect_risk, detect_goal, extract_budget, build_allocation

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# CORE ENGINE (REUSABLE)
# =========================
def advisor_core(user_email: str, message: str, level: str):

    budget = extract_budget(message)
    risk = detect_risk(message)
    goal = detect_goal(message)
    allocation = build_allocation(budget, risk)

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")
    business = get_business_intelligence(user_email)

    prompt = f"""
Tu es un AI advisor de type hedge fund.

LEVEL: {level}

USER MESSAGE:
{message}

BUDGET:
{budget}

RISK:
{risk}

GOAL:
{goal}

ALLOCATION SUGGÉRÉE:
{json.dumps(allocation, indent=2)}

PORTFOLIO:
{portfolio}

MARKET:
{market}

BUSINESS OPPORTUNITIES:
{business}

INSTRUCTIONS:
- Donne une stratégie claire
- Donne allocation concrète
- Donne 3 actions immédiates
- Optimise rendement vs risque
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "level": level,
        "budget": budget,
        "risk": risk,
        "goal": goal,
        "allocation": allocation,
        "advice": response.choices[0].message.content
    }


# =========================
# TIERS (IMPORTANT POUR STRIPE)
# =========================

def get_advisor_free(user_email, message):
    return advisor_core(user_email, message, level="FREE")


def get_advisor_premium(user_email, message):
    return advisor_core(user_email, message, level="PREMIUM")


def get_advisor_elite(user_email, message):
    return advisor_core(user_email, message, level="ELITE")
