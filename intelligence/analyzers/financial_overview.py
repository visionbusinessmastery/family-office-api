# =========================
# IMPORTS
# =========================
# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine


# =========================
# SAFE EXECUTION WRAPPER
# =========================
def safe_fetchall(conn, query, params):
    try:
        return conn.execute(text(query), params).fetchall()
    except Exception as e:
        print(f"[FINANCIAL ENGINE WARNING] {e}")
        return []


# =========================
# USER FINANCIAL OVERVIEW (ROBUST)
# =========================
def get_user_financial_overview(user_id: int):

    with engine.connect() as conn:

        # =========================
        # INCOME
        # =========================
        income_rows = safe_fetchall(conn, """
            SELECT type, amount
            FROM user_income
            WHERE user_id = :user_id
        """, {"user_id": user_id})

        income_sources = []
        total_income = 0

        for r in income_rows:
            amount = float(r.amount or 0)

            income_sources.append({
                "type": r.type or "unknown",
                "amount": amount
            })

            total_income += amount

        # =========================
        # DEBT
        # =========================
        debt_rows = safe_fetchall(conn, """
            SELECT name, monthly_payment, total_debt
            FROM user_debts
            WHERE user_id = :user_id
        """, {"user_id": user_id})

        debts = []
        total_debt = 0
        monthly_debt_payment = 0

        for r in debt_rows:
            monthly = float(r.monthly_payment or 0)
            total = float(r.total_debt or 0)

            debts.append({
                "name": r.name or "debt",
                "monthly_payment": monthly,
                "total_debt": total
            })

            monthly_debt_payment += monthly
            total_debt += total

        # =========================
        # SAVINGS
        # =========================
        savings_rows = safe_fetchall(conn, """
            SELECT account_name, balance
            FROM user_savings
            WHERE user_id = :user_id
        """, {"user_id": user_id})

        savings_accounts = []
        total_savings = 0

        for r in savings_rows:
            balance = float(r.balance or 0)

            savings_accounts.append({
                "account": r.account_name or "account",
                "balance": balance
            })

            total_savings += balance

        # =========================
        # CASHFLOW
        # =========================
        net_cashflow = total_income - monthly_debt_payment

        return {
            "totals": {
                "monthly_income": total_income,
                "monthly_debt_payment": monthly_debt_payment,
                "total_debt": total_debt,
                "total_savings": total_savings,
                "net_cashflow": net_cashflow
            },
            "income_sources": income_sources,
            "debts": debts,
            "savings_accounts": savings_accounts
        }
