from openai import OpenAI
import os
import json

from business.service import get_business_intelligence
from portfolio.service import get_user_portfolio
from market.service import get_market

from advisor.engine import (
    detect_risk,
    extract_budget
)

from advisor.portfolio_ai import (
    score_portfolio,
    generate_actions,
    optimal_allocation
)

from advisor.autopilot import autopilot_engine
from advisor.engine import detect_risk, extract_budget


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def portfolio_manager(user_email: str, message: str, level="free"):

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")
    intelligence = get_business_intelligence(user_email)

    budget = extract_budget(message)
    risk = detect_risk(message)

    # =========================
    # 1. SCORING ENGINE
    # =========================
    score = score_portfolio(portfolio, market)

    # =========================
    # 2. ACTION ENGINE
    # =========================
    actions = generate_actions(score)

    # =========================
    # 3. TARGET ALLOCATION
    # =========================
    allocation = optimal_allocation(risk)

    # =========================
    # 4. AI STRATEGY LAYER
    # =========================
    prompt = f"""
    Tu es un Portfolio Manager quant institutionnel.

    SCORE PORTFOLIO:
    {json.dumps(score, indent=2)}

    ACTIONS:
    {actions}

    ALLOCATION CIBLE:
    {json.dumps(allocation, indent=2)}

    USER MESSAGE:
    {message}

    Donne :
    - analyse portefeuille
    - risques majeurs
    - plan d'action
    - recommandation précise
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "score": score,
        "actions": actions,
        "allocation": allocation,
        "advice": response.choices[0].message.content
    }


def portfolio_autopilot(user_email, message):

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    risk = detect_risk(message)

    system = autopilot_engine(
        user_email,
        portfolio,
        market,
        risk
    )

    return system
