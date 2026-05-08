XP_RULES = {
    "login": 5,
    "view_dashboard": 3,
    "add_finance_item": 15,
    "update_portfolio": 20,
    "complete_onboarding": 50,
    "connect_account": 40,
    "ai_interaction": 10,
    "daily_quest_complete": 30
}


def compute_xp(action: str, streak: int = 0, liberty_mode=False):

    base_xp = XP_RULES.get(action, 0)

    bonus = 0

    # 🔥 streak multiplier
    if streak >= 30:
        bonus += 0.5
    elif streak >= 14:
        bonus += 0.25
    elif streak >= 7:
        bonus += 0.15
    elif streak >= 3:
        bonus += 0.10

    # 🔥 liberty multiplier
    if liberty_mode:
        bonus += 0.50

    return int(base_xp * (1 + bonus))
