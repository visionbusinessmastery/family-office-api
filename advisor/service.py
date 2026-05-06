from openai import OpenAI
import os
import json

from intelligence.orchestrator import run_orchestrator

from portfolio.service import get_user_portfolio
from market.service import get_market

from advisor.engine import detect_risk, extract_budget
from advisor.autopilot_v4_engine import AutopilotV4

from advisor.decision_engine import (
    extract_decision,
    validate_decision,
    build_execution_plan
)

from advisor.execution_engine import execute_autopilot_actions
from advisor.log_engine import log_autopilot_event
from advisor.performance_engine import compute_performance
from advisor.decision_scoring import score_decision


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# =========================
# SMART ADVISOR + AUTOPILOT
# =========================
def advisor_logic(user_email, message, level="free"):

    context = run_orchestrator(user_email)

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    # =========================
    # 1. GPT DECISION
    # =========================
    prompt = f"""
    Tu es un AI Family Office.

    OBJECTIF :
    - comprendre l'intention utilisateur
    - proposer une stratégie
    - suggérer une action claire

    CONTEXTE :
    {json.dumps(context, indent=2)}

    MESSAGE :
    {message}

    Réponds avec :
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
    # 2. DECISION ENGINE
    # =========================
    decision = extract_decision(llm_text)
    decision = validate_decision(decision, context)
    execution_plan = build_execution_plan(decision)

    # =========================
    # 3. AUTOPILOT EXECUTION
    # =========================
    autopilot_result = None

    if execution_plan["execute"]:
        autopilot_result = autopilot_engine(
            user_email=user_email,
            portfolio=portfolio,
            market=market,
            risk_level=execution_plan["risk_level"]
        )

    # =========================
    # 4. FINAL OUTPUT
    # =========================
    return {
        "analysis": llm_text,
        "decision": decision,
        "execution": execution_plan,
        "autopilot": autopilot_result,
        "context_score": context.get("score")
    }


# =========================
# PUBLIC ENDPOINTS
# =========================
def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message, "free")


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message, "premium")


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message, "elite")



def portfolio_autopilot(user_email, message):

    from intelligence.orchestrator import run_orchestrator

    context = run_orchestrator(user_email)

    portfolio = get_user_portfolio(user_email)
    market = get_market("global")

    risk = detect_risk(message)

    engine = AutopilotV4()

    # =========================
    # 1. CORE AUTOPILOT
    # =========================
    system = autopilot_engine(
        user_email,
        portfolio,
        market,
        risk
    )

    actions = system.get("actions", [])
    strategy = system.get("strategy", [])

    # =========================
    # 2. EXECUTION
    # =========================
    trades = execute_actions(user_email, actions, market)

    # =========================
    # 3. PERFORMANCE
    # =========================
    performance = compute_performance(user_email)

    # =========================
    # 4. DECISION SCORE
    # =========================
    decision_score = score_decision(actions, performance)

    # =========================
    # 5. LOGGING
    # =========================
    log_event(
        user_email,
        actions,
        strategy,
        system.get("score", {})
    )

    # =========================
    # FINAL OUTPUT
    # =========================
    return {
        "context": context.get("score"),
        "autopilot": system,
        "trades": trades,
        "performance": performance,
        "decision_score": decision_score
    }
