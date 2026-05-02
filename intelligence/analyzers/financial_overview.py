# =========================
# IMPORTS
# =========================
from sqlalchemy import text
from database import engine

# =========================
# USER FINANCIAL OVERVIEW
# =========================
def get_user_financial_overview(user_id: int):

    with engine.connect() as conn:

        # =========================
        # INCOME (multi-sources)
        # =========================
        income_rows = conn.execute(text("""
            SELECT type, amount
            FROM user_income
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        income_sources = []
        total_income = 0

        for r in income_rows:
            income_sources.append({
                "type": r.type,
                "amount": float(r.amount)
            })
            total_income += float(r.amount)

        # =========================
        # DEBT
        # =========================
        debt_rows = conn.execute(text("""
            SELECT name, monthly_payment, total_debt
            FROM user_debts
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        total_debt = 0
        monthly_debt_payment = 0

        debts = []

        for r in debt_rows:
            debts.append({
                "name": r.name,
                "monthly_payment": float(r.monthly_payment),
                "total_debt": float(r.total_debt)
            })

            monthly_debt_payment += float(r.monthly_payment)
            total_debt += float(r.total_debt)

        # =========================
        # SAVINGS (multi comptes)
        # =========================
        savings_rows = conn.execute(text("""
            SELECT account_name, balance
            FROM user_savings
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchall()

        savings_accounts = []
        total_savings = 0

        for r in savings_rows:
            savings_accounts.append({
                "account": r.account_name,
                "balance": float(r.balance)
            })
            total_savings += float(r.balance)

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
