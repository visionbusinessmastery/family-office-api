# =========================
# AI ALLOCATION ENGINE
# =========================

def compute_allocation_strategy(context: dict):

    risk = context.get(
        "risk_profile",
        "medium"
    )

    if risk == "low":

        allocation = {
            "cash": 30,
            "bonds": 40,
            "etf": 20,
            "crypto": 10,
        }

    elif risk == "high":

        allocation = {
            "stocks": 35,
            "crypto": 35,
            "private_equity": 20,
            "cash": 10,
        }

    else:

        allocation = {
            "stocks": 30,
            "etf": 30,
            "real_estate": 20,
            "crypto": 10,
            "cash": 10,
        }

    return allocation
