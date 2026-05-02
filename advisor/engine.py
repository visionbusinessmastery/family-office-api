import re


def extract_budget(message: str):
    match = re.search(r'(\d+)', message.replace(",", ""))
    return float(match.group(1)) if match else 1000


def detect_risk(message: str):
    message = message.lower()

    if any(x in message for x in ["safe", "sécur", "prudence"]):
        return "low"
    if any(x in message for x in ["agressif", "risqué", "risk"]):
        return "high"
    return "medium"


def detect_goal(message: str):
    message = message.lower()

    if "revenu" in message:
        return "income"
    if "rapide" in message:
        return "short_term"
    return "long_term"


def build_allocation(risk: str):

    allocations = {
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

    return allocations[risk]
