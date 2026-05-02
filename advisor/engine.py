import re


# =========================
# BUDGET EXTRACTION (robuste)
# =========================
def extract_budget(message: str):
    message = message.lower().replace(" ", "")

    # cas 10k / 10K
    match_k = re.search(r"(\d+)[kK]", message)
    if match_k:
        return float(match_k.group(1)) * 1000

    # cas 10 000 / 10000
    match = re.search(r"(\d{3,})", message)
    if match:
        return float(match.group(1))

    return 1000  # fallback


# =========================
# RISK DETECTION (amélioré)
# =========================
def detect_risk(message: str):
    message = message.lower()

    high_risk_keywords = [
        "agressif", "risqué", "risque", "high risk",
        "leveraged", "levier", "speculatif"
    ]

    low_risk_keywords = [
        "safe", "sécur", "sécurisé", "low risk",
        "stable", "sécurité", "sans risque"
    ]

    if any(word in message for word in high_risk_keywords):
        return "high"

    if any(word in message for word in low_risk_keywords):
        return "low"

    return "medium"


# =========================
# GOAL DETECTION
# =========================
def detect_goal(message: str):
    message = message.lower()

    if any(w in message for w in ["revenu", "income", "cashflow", "cash flow"]):
        return "income"

    if any(w in message for w in ["rapide", "short", "quick", "court terme"]):
        return "short_term"

    if any(w in message for w in ["long", "patrimoine", "wealth", "build"]):
        return "long_term"

    return "long_term"


# =========================
# ALLOCATION ENGINE
# =========================
def build_allocation(budget, risk):

    base = {
        "real_estate": 25,
        "stocks": 30,
        "crypto": 15,
        "business": 20,
        "crowdfunding": 10
    }

    if risk == "low":
        base = {
            "real_estate": 40,
            "stocks": 35,
            "crypto": 5,
            "business": 15,
            "crowdfunding": 5
        }

    elif risk == "high":
        base = {
            "real_estate": 10,
            "stocks": 25,
            "crypto": 35,
            "business": 20,
            "crowdfunding": 10
        }

    # convert % → money allocation
    allocation = {
        k: round(budget * v / 100, 2)
        for k, v in base.items()
    }

    return {
        "percent": base,
        "allocation": allocation,
        "total": budget
    }
