# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine


def get_user_financial_overview(user_id: int):

    with engine.connect() as conn:

        income = conn.execute(text("""
            SELECT type, amount FROM user_income WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        debts = conn.execute(text("""
            SELECT name, monthly_payment, total_debt FROM user_debts WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        savings = conn.execute(text("""
            SELECT account_name, balance FROM user_savings WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().all()

        total_income = sum(float(i["amount"] or 0) for i in income)
        total_debt = sum(float(d["total_debt"] or 0) for d in debts)
        total_savings = sum(float(s["balance"] or 0) for s in savings)

        return {
            "totals": {
                "monthly_income": total_income,
                "total_debt": total_debt,
                "total_savings": total_savings,
                "net_cashflow": total_income - total_debt
            },
            "income_sources": income,
            "debts": debts,
            "savings_accounts": savings
        }
