# =========================
# DECISION ENGINE V3
# =========================

import json


# =========================
# PARSE LLM OUTPUT
# =========================
def extract_decision(llm_text: str):

    decision = {
        "intent": "unknown",
        "risk": "medium",
        "action": None
    }

    text = llm_text.lower()

    if "invest" in text or "allocation" in text:
        decision["intent"] = "invest"

    elif "rebalance" in text:
        decision["intent"] = "rebalance"

    elif "sell" in text or "reduce" in text:
        decision["intent"] = "reduce_risk"

    # risk detection
    if "safe" in text or "sécur" in text:
        decision["risk"] = "low"
    elif "agressif" in text or "high risk" in text:
        decision["risk"] = "high"

    return decision


# =========================
# VALIDATION LAYER
# =========================
def validate_decision(decision: dict, context: dict):

    level = context.get("level", "FREE")

    # 🔒 FREE restrictions
    if level == "FREE":
        decision["execution_allowed"] = False
        decision["reason"] = "upgrade_required"
        return decision

    decision["execution_allowed"] = True
    return decision


# =========================
# FINAL DECISION BUILDER
# =========================
def build_execution_plan(decision: dict):

    if not decision.get("execution_allowed"):
        return {
            "execute": False,
            "reason": decision.get("reason")
        }

    return {
        "execute": True,
        "risk_level": decision.get("risk"),
        "intent": decision.get("intent")
    }
