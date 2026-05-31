import time
from collections import defaultdict

# =========================
# SIMPLE MEMORY RATE LIMIT (V1 LOCAL)
# =========================

USER_DAILY_USAGE = defaultdict(list)

FREE_DAILY_LIMIT = 20        # appels max / jour
FREE_HARD_BLOCK = True       # blocage strict
RESET_INTERVAL = 86400       # 24h

def _cleanup(user_id):
    """Supprime les appels > 24h"""
    now = time.time()
    USER_DAILY_USAGE[user_id] = [
        t for t in USER_DAILY_USAGE[user_id]
        if now - t < RESET_INTERVAL
    ]


def register_call(user_id: str):
    USER_DAILY_USAGE[user_id].append(time.time())


def get_usage(user_id: str):
    _cleanup(user_id)
    return len(USER_DAILY_USAGE[user_id])


def check_budget(user_id: str, plan: str):
    """
    Retourne:
    - allowed: bool
    - reason: str
    """

    usage = get_usage(user_id)

    # FREE TIER STRICT
    if plan == "FREE":
        if usage >= FREE_DAILY_LIMIT:
            return {
                "allowed": False,
                "reason": "FREE_LIMIT_REACHED",
                "usage": usage
            }

    return {
        "allowed": True,
        "reason": "OK",
        "usage": usage
    }
