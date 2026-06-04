import time
from collections import defaultdict

from security.abuse_engine import PLAN_ETHAN_LIMITS


USER_DAILY_USAGE = defaultdict(list)

RESET_INTERVAL = 86400


def _cleanup(user_id):
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
    usage = get_usage(user_id)

    limit = PLAN_ETHAN_LIMITS.get(plan, PLAN_ETHAN_LIMITS["FREE"])

    if usage >= limit:
        return {
            "allowed": False,
            "reason": "LIMIT_REACHED",
            "usage": usage,
            "limit": limit
        }

    return {
        "allowed": True,
        "reason": "OK",
        "usage": usage,
        "limit": limit
    }