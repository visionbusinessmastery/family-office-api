# =========================
# AI ADVISOR ENGINE V2
# =========================

import os
import json
import hashlib
from openai import OpenAI

from intelligence.core.orchestrator import run_orchestrator
from portfolio.service import get_user_portfolio
from market.service import get_market
from advisor.autopilot_v4_engine import get_autopilot_v4

from core.cache import redis_client

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# HASH BUILDER (LLM CACHE)
# =========================
def build_hash(user_email, message, level):

    raw = json.dumps(
        {
            "email": user_email,
            "message": message,
            "level": level
        },
        sort_keys=True
    )

    return hashlib.md5(raw.encode()).hexdigest()


# =========================
# MAIN ADVISOR
# =========================
def advisor_logic(user_email, message, level="free"):

    # =========================
    # CACHE KEY (FULL REQUEST)
    # =========================
    cache_key = (
        f"advisor:{build_hash(user_email, message, level)}"
    )

    cached = get_cache(cache_key)
    if cached:
        return cached

    # =========================
    # CONTEXT ENGINE
    # =========================
    context = run_orchestrator(user_email)

    # =========================
    # DATA SOURCES (CACHED)
    # =========================
    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    opportunities = context.get("opportunities", [])

    # =========================
    # LLM PROMPT
    # =========================
    prompt = f"""
Tu es un AI Family Office ultra avancé.

CONTEXTE GLOBAL:
{json.dumps(context, indent=2)}

PORTEFEUILLE:
{json.dumps(portfolio, indent=2)}

OPPORTUNITÉS:
{json.dumps(opportunities, indent=2)}

MESSAGE UTILISATEUR:
{message}

Donne :
- analyse patrimoniale
- stratégie
- risques
- opportunités
- plan d'action concret
"""

    # =========================
    # CACHE LLM RESPONSE (IMPORTANT SAAS OPTIMIZATION)
    # =========================
    llm_cache_key = f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"

    llm_text = get_cache(llm_cache_key)

    if not llm_text:

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        llm_text = response.choices[0].message.content

        set_cache(llm_cache_key, llm_text, ttl=600)

    # =========================
    # AUTOPILOT ENGINE
    # =========================
    autopilot = get_autopilot_v4()

    autopilot_result = autopilot.run(
        user_email=user_email,
        portfolio=portfolio,
        market=market,
        context=context,
        llm_analysis=llm_text,
        level=level
    )

    # =========================
    # FINAL RESULT
    # =========================
    result = {
        "analysis": llm_text,
        "context_score": context.get("global_score") or context.get("score"),
        "autopilot": autopilot_result
    }

    set_cache(cache_key, result, ttl=300)

    return result


# =========================
# API WRAPPERS
# =========================
def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, "free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, "premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, "elite")


# =========================
# SIMPLE MODULES
# =========================
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
