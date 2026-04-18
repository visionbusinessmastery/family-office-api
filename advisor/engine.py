import re

def extract_budget(message: str):
    match = re.search(r'(\d+)', message.replace(",", "").lower())
    if match:
        return float(match.group(1))
    return 1000  # fallback


def detect_risk(message: str):
    message = message.lower()

    if "safe" in message or "sécur" in message:
        return "low"
    elif "agressif" in message or "risqué" in message:
        return "high"
    return "medium"


def detect_goal(message: str):
    if "revenu" in message:
        return "income"
    elif "rapide" in message:
        return "short_term"
    return "long_term"

def build_allocation(budget, risk):

    if risk == "low":
        return {
            "real_estate": 40,
            "stocks": 30,
            "crypto": 5,
            "business": 15,
            "crowdfunding": 10
        }

    elif risk == "high":
        return {
            "real_estate": 10,
            "stocks": 30,
            "crypto": 30,
            "business": 20,
            "crowdfunding": 10
        }

    return {
        "real_estate": 25,
        "stocks": 30,
        "crypto": 15,
        "business": 20,
        "crowdfunding": 10
    }
