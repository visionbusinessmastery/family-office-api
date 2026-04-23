from datetime import datetime

def get_plan_from_score(score: int):

    if score >= 85:
        return "ELITE"
    elif score >= 70:
        return "GOLD"
    elif score >= 50:
        return "SILVER"
    else:
        return "FREE"


def compute_upgrade_decision(current_plan: str, score: int):

    recommended_plan = get_plan_from_score(score)

    hierarchy = {
        "FREE": 0,
        "SILVER": 1,
        "GOLD": 2,
        "ELITE": 3
    }

    current_level = hierarchy.get(current_plan or "FREE", 0)
    recommended_level = hierarchy.get(recommended_plan, 0)

    # =========================
    # CASE 1: UPGRADE POSSIBLE
    # =========================
    if recommended_level > current_level:

        return {
            "upgrade": True,
            "from": current_plan,
            "to": recommended_plan,
            "recommended_plan": recommended_plan,
            "auto_apply": recommended_plan == "ELITE"  # auto upgrade ONLY ELITE (option safe SaaS)
        }

    # =========================
    # CASE 2: NO CHANGE
    # =========================
    return {
        "upgrade": False,
        "from": current_plan,
        "to": current_plan,
        "recommended_plan": recommended_plan,
        "auto_apply": False
    }
