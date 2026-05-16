# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine
from core.cache import redis_client
import json


# =========================
# CACHE HELPERS
# =========================
def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except:
        pass


# =========================
# FINANCIAL OVERVIEW ENGINE (OPTIMIZED)
# =========================
def get_user_financial_overview(user_id: int):

    cache_key = f"financial:{user_id}"

    # =========================
    # CACHE CHECK
    # =========================
    cached = get_cache(cache_key)
    if cached:
        return cached

    with engine.connect() as conn:

        # =========================
        # INCOME
        # =========================
        income = conn.execute(text("""
            SELECT type, amount
            FROM user_income
            WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        # =========================
        # DEBTS
        # =========================
        debts = conn.execute(text("""
            SELECT name, monthly_payment, total_debt
            FROM user_debts
            WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        # =========================
        # SAVINGS
        # =========================
        savings = conn.execute(text("""
            SELECT account_name, balance
            FROM user_savings
            WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        # =========================
        # SAFE SUMS
        # =========================
        total_income = sum(float(i.get("amount") or 0) for i in income)
        total_debt = sum(float(d.get("total_debt") or 0) for d in debts)
        total_savings = sum(float(s.get("balance") or 0) for s in savings)

        result = {
            "totals": {
                "monthly_income": total_income,
                "total_debt": total_debt,
                "total_savings": total_savings,
                "net_cashflow": total_income - total_debt
            },
            "income_sources": list(income),
            "debts": list(debts),
            "savings_accounts": list(savings)
        }

    # =========================
    # CACHE STORE
    # =========================
    set_cache(cache_key, result, ttl=300)

    return result
