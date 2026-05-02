import re

def extract_budget(message: str):
    match = re.search(r'(\d+)', message.replace(",", ""))
    return float(match.group(1)) if match else 1000


def detect_risk(message: str):
    message = message.lower()

    if any(x in message for x in ["safe", "sécur", "prud"]):
        return "low"
    elif any(x in message for x in ["agressif", "risqué", "high"]):
        return "high"
    return "medium"


def detect_goal(message: str):
    message = message.lower()

    if "revenu" in message:
        return "income"
    elif "rapide" in message:
        return "short_term"
    return "long_term"


def build_allocation(budget, risk):

    base = {
        "real_estate": 25,
        "stocks": 30,
        "crypto": 15,
        "business": 20,
        "crowdfunding": 10
    }

    if risk == "low":
        return {
            "real_estate": 40,
            "stocks": 35,
            "crypto": 5,
            "business": 10,
            "crowdfunding": 10
        }

    if risk == "high":
        return {
            "real_estate": 10,
            "stocks": 25,
            "crypto": 35,
            "business": 20,
            "crowdfunding": 10
        }

    return base
