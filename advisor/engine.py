# =========================
# AI ADVISOR ENGINE V4 (CLEAN BRAIN)
# =========================

import re

from intelligence.user_intelligence_engine import compute_user_intelligence


# =========================
# PARSING INPUT
# =========================
def extract_budget(message: str):
    match = re.search(r'(\d+)', message.replace(",", ""))
    return float(match.group(1)) if match else 1000


def detect_risk(message: str):
    msg = message.lower()

    if "safe" in msg or "sécur" in msg:
        return "low"
    if "agressif" in msg or "risqué" in msg:
        return "high"
    return "medium"


def detect_goal(message: str):
    msg = message.lower()

    if "revenu" in msg:
        return "income"
    if "rapide" in msg:
        return "short_term"
    return "long_term"


# =========================
# STRATEGY ENGINE
# =========================
def build_allocation(risk: str):

    base = {
        "low": {
            "real_estate": 40,
            "stocks": 30,
            "crypto": 5,
            "business": 15,
            "crowdfunding": 10
        },
        "medium": {
            "real_estate": 25,
            "stocks": 30,
            "crypto": 15,
            "business": 20,
            "crowdfunding": 10
        },
        "high": {
            "real_estate": 10,
            "stocks": 30,
            "crypto": 30,
            "business": 20,
            "crowdfunding": 10
        }
    }

    return base.get(risk, base["medium"])


# =========================
# ADVISOR CORE
# =========================
def run_advisor(user_email: str, message: str):

    intelligence = compute_user_intelligence(user_email)

    if not intelligence or "error" in intelligence:
        return {"error": "INTELLIGENCE_FAILED"}

    score = intelligence.get("score", {}).get("score", 0)
    level = intelligence.get("level", "BEGINNER")

    risk = detect_risk(message)
    goal = detect_goal(message)
    budget = extract_budget(message)

    allocation = build_allocation(risk)

    # =========================
    # STRATEGY LOGIC
    # =========================
    if score < 40:
        strategy = "Foundation building"
        next_action = "Increase savings + stabilize income"
    elif score < 70:
        strategy = "Optimization phase"
        next_action = "Diversify assets"
    else:
        strategy = "Scaling phase"
        next_action = "Access premium opportunities"

    # =========================
    # FINAL OUTPUT
    # =========================
    return {
        "user": user_email,

        "advisor": {
            "strategy": strategy,
            "next_action": next_action,
            "risk": risk,
            "goal": goal,
            "budget": budget
        },

        "allocation": allocation,

        "intelligence": {
            "score": score,
            "level": level
        }
    }
