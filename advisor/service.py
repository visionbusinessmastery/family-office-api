from openai import OpenAI
import os
import json

from intelligence.orchestrator import run_orchestrator
from portfolio.service import get_user_portfolio
from market.service import get_market

from advisor.autopilot_v4_engine import get_autopilot_v4

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# MAIN ADVISOR
# =========================
def advisor_logic(user_email, message, level="free"):

    # =========================
    # CONTEXT ENGINE (GLOBAL STATE)
    # =========================
    context = run_orchestrator(user_email)

    # =========================
    # DATA SOURCES
    # =========================
    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    # =========================
    # LLM ANALYSIS (GPT)
    # =========================
    prompt = f"""
    Tu es un AI Family Office intelligent.

    CONTEXTE GLOBAL:
    {json.dumps(context, indent=2)}

    PORTEFEUILLE:
    {json.dumps(portfolio, indent=2)}

    MESSAGE UTILISATEUR:
    {message}

    Réponds clairement avec :
    - analyse
    - stratégie
    - action recommandée
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    llm_text = response.choices[0].message.content

    # =========================
    # AUTOPILOT V4 ENGINE 🔥
    # =========================
    autopilot_engine = get_autopilot_v4()

    autopilot_result = autopilot_engine.run(
        user_email=user_email,
        portfolio=portfolio,
        market=market,
        context=context,
        llm_analysis=llm_text,
        level=level
    )

    # =========================
    # FINAL OUTPUT
    # =========================
    return {
        "analysis": llm_text,
        "context_score": context.get("score"),
        "autopilot": autopilot_result
    }


def portfolio_manager(user_email, message):
    return {
        "status": "ok",
        "message": "Portfolio manager not implemented yet",
        "user": user_email
    }


def portfolio_autopilot(user_email, message):
    engine = get_autopilot_v4()

    return engine.run(
        user_email=user_email,
        portfolio=get_user_portfolio(user_email),
        market=get_market("global"),
        context={},
        llm_analysis=message,
        level="free"
    )

# =========================
# PUBLIC API
# =========================
def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, "free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, "premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, "elite")
