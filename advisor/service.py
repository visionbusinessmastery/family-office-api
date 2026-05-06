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

    context = run_orchestrator(user_email)

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    prompt = f"""
    Tu es un AI Family Office.

    CONTEXTE:
    {json.dumps(context, indent=2)}

    MESSAGE:
    {message}

    Donne:
    - analyse
    - stratégie
    - action
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    llm_text = response.choices[0].message.content

    return {
        "analysis": llm_text,
        "context_score": context.get("score")
    }


def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, "free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, "premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, "elite")
