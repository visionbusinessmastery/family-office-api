# =========================
# AI ADVISOR ENGINE V2
# =========================

import hashlib
import json
import os

from openai import OpenAI

from advisor.autopilot_v4_engine import get_autopilot_v4
from auth.utils import get_user_id
from core.cache import redis_client
from database import engine
from intelligence.core.orchestrator import run_orchestrator
from market.service import get_market
from portfolio.service import get_user_portfolio

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def build_hash(user_email, message, level):
    raw = json.dumps(
        {"email": user_email, "message": message, "level": level},
        sort_keys=True,
    )
    return hashlib.md5(raw.encode()).hexdigest()


def advisor_logic(user_email, message, level="free"):
    cache_key = f"advisor:{build_hash(user_email, message, level)}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    context = run_orchestrator(user_email)
    user_id = None

    with engine.connect() as conn:
        user_id = get_user_id(conn, user_email)

    portfolio = get_user_portfolio(user_id) if user_id else {}
    market = get_market("global")
    opportunities = context.get("opportunities", [])

    prompt = build_advisor_prompt(context, portfolio, opportunities, message)
    llm_text = get_llm_response(prompt)

    if not llm_text:
        result = build_fallback_response(context, opportunities)
        set_cache(cache_key, result, ttl=120)
        return result

    result = {
        "analysis": llm_text,
        "context_score": get_context_score(context),
        "autopilot": run_autopilot_safely(
            user_email=user_email,
            portfolio=portfolio,
            market=market,
            context=context,
            llm_text=llm_text,
            level=level,
        ),
    }

    set_cache(cache_key, result, ttl=300)
    return result


def build_advisor_prompt(context, portfolio, opportunities, message):
    return f"""
Tu es un AI Family Office ultra avance.

CONTEXTE GLOBAL:
{json.dumps(context, indent=2)}

PORTEFEUILLE:
{json.dumps(portfolio, indent=2)}

OPPORTUNITES:
{json.dumps(opportunities, indent=2)}

MESSAGE UTILISATEUR:
{message}

Donne :
- analyse patrimoniale
- strategie
- risques
- opportunites
- plan d'action concret
"""


def get_llm_response(prompt):
    llm_cache_key = f"llm:{hashlib.md5(prompt.encode()).hexdigest()}"

    cached = get_cache(llm_cache_key)
    if cached:
        return cached

    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        llm_text = response.choices[0].message.content
        set_cache(llm_cache_key, llm_text, ttl=600)
        return llm_text
    except Exception:
        return None


def run_autopilot_safely(user_email, portfolio, market, context, llm_text, level):
    try:
        autopilot = get_autopilot_v4()
        return autopilot.run(
            user_email=user_email,
            portfolio=portfolio,
            market=market,
            context=context,
            llm_analysis=llm_text,
            level=level,
        )
    except Exception as e:
        return {"status": "unavailable", "message": str(e)}


def get_context_score(context):
    score = context.get("global_score") or context.get("score", 0)

    if isinstance(score, dict):
        return score.get("score", 0)

    return score


def build_fallback_response(context, opportunities):
    score = get_context_score(context)
    opportunity_count = (
        len(opportunities)
        if isinstance(opportunities, list)
        else opportunities.get("count", 0)
        if isinstance(opportunities, dict)
        else 0
    )

    return {
        "analysis": (
            "Je peux deja t'aider avec les donnees disponibles. "
            f"Ton score actuel est {score}/100. "
            f"J'ai detecte {opportunity_count} opportunite(s) liee(s) a ton profil. "
            "Pour augmenter ton capital, priorise: augmenter ton cashflow mensuel, "
            "reduire les charges recurrentes, diversifier les actifs trop concentres, "
            "et reinvestir regulierement les plus-values dans les zones les mieux scorees."
        ),
        "context_score": score,
        "autopilot": None,
    }


def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, "free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, "premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, "elite")


def portfolio_manager(user_email, message):
    return {
        "status": "ok",
        "message": "Portfolio manager not implemented yet",
        "user": user_email,
    }


def portfolio_autopilot(user_email, message):
    user_id = None

    with engine.connect() as conn:
        user_id = get_user_id(conn, user_email)

    return run_autopilot_safely(
        user_email=user_email,
        portfolio=get_user_portfolio(user_id) if user_id else {},
        market=get_market("global"),
        context={},
        llm_text=message,
        level="free",
    )
