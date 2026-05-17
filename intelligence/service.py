# =========================
# IMPORTS CLEAN
# =========================
from intelligence.engines.allocation_engine import compute_allocation_strategy
from intelligence.scoring.family_office_score import compute_family_office_score
from intelligence.scoring.financial_overview import get_user_financial_overview

from sqlalchemy import text
from database import engine


# =========================
# NORMALISATION RISQUE
# =========================
def normalize_risk(risk: str):

    if not risk:
        return "modéré"

    r = risk.lower().strip()

    mapping = {
        "faible": "faible",
        "low": "faible",

        "modéré": "modéré",
        "modere": "modéré",
        "medium": "modéré",

        "élevé": "élevé",
        "eleve": "élevé",
        "high": "élevé"
    }

    return mapping.get(r, "modéré")


# =========================
# GLOBAL INTELLIGENCE ENGINE
# =========================
def get_global_intelligence(query):

    try:

        risk = normalize_risk(query.risk)

        # =========================
        # SAFE DEFAULT DATA
        # =========================
        real_data = []
        crypto_data = {"BTC": 1}
        stock_data = {"AAPL": 1}

        # =========================
        # FIX QUERY
        # =========================
        query.risk = risk

        # =========================
        # ALLOCATION ENGINE SAFE
        # =========================
        allocation = compute_allocation_strategy(
            budget=getattr(query, "budget", 0),
            risk=risk,
            real_estate=real_data,
            crypto=crypto_data,
            stocks=stock_data
        )

        # =========================
        # SIMPLE AI LAYER (SAFE FALLBACK)
        # =========================
        ai = {
            "summary": "Analyse globale générée",
            "risk": risk,
            "allocation_score": allocation.get("score", 0) if isinstance(allocation, dict) else 0
        }

        return {
            "real_estate": real_data[:3] if isinstance(real_data, list) else [],
            "crypto": crypto_data,
            "stocks": stock_data,
            "allocation": allocation,
            "ai_global": ai
        }

    except Exception as e:
        return {"error": str(e)}


# =========================
# USER FINANCIAL OVERVIEW
# =========================
def get_user_financial_overview(user_id):

    try:

        with engine.connect() as conn:

            # =========================
            # INCOME
            # =========================
            income_rows = conn.execute(text("""
                SELECT name, income_type, monthly_income
                FROM income_sources
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

            income_sources = []
            total_income = 0

            for r in income_rows:

                income = float(r.monthly_income or 0)

                income_sources.append({
                    "name": r.name,
                    "type": r.income_type,
                    "monthly_income": income
                })

                total_income += income

            # =========================
            # DEBTS
            # =========================
            debt_rows = conn.execute(text("""
                SELECT name, debt_type, remaining_amount, monthly_payment
                FROM debts
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

            debts = []
            total_debt = 0
            total_monthly_debt = 0

            for r in debt_rows:

                remaining = float(r.remaining_amount or 0)
                monthly = float(r.monthly_payment or 0)

                debts.append({
                    "name": r.name,
                    "type": r.debt_type,
                    "remaining_amount": remaining,
                    "monthly_payment": monthly
                })

                total_debt += remaining
                total_monthly_debt += monthly

            # =========================
            # SAVINGS
            # =========================
            savings_rows = conn.execute(text("""
                SELECT name, bank, balance, currency
                FROM savings_accounts
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

            savings = []
            total_savings = 0

            for r in savings_rows:

                bal = float(r.balance or 0)

                savings.append({
                    "name": r.name,
                    "bank": r.bank,
                    "balance": bal,
                    "currency": r.currency
                })

                total_savings += bal

        # =========================
        # KPIs
        # =========================
        net_cashflow = total_income - total_monthly_debt
        net_worth = total_savings - total_debt

        savings_rate = (total_savings / total_income * 100) if total_income > 0 else 0
        debt_ratio = (total_debt / (total_savings + 1)) * 100

        return {
            "income_sources": income_sources,
            "debts": debts,
            "savings": savings,

            "totals": {
                "monthly_income": round(total_income, 2),
                "monthly_debt_payment": round(total_monthly_debt, 2),
                "total_debt": round(total_debt, 2),
                "total_savings": round(total_savings, 2),

                "net_cashflow": round(net_cashflow, 2),
                "net_worth_estimate": round(net_worth, 2),

                "savings_rate": round(savings_rate, 2),
                "debt_ratio": round(debt_ratio, 2)
            }
        }

    except Exception as e:
        return {"error": str(e)}


# =========================
# FAMILY OFFICE SCORE
# =========================
def get_family_office_score(user_email):

    try:

        with engine.connect() as conn:

            # PROFILE
            profile_row = conn.execute(text("""
                SELECT savings, investments, risk_profile
                FROM user_profiles
                WHERE user_email=:email
            """), {"email": user_email}).fetchone()

            profile = dict(profile_row._mapping) if profile_row else {
                "savings": 0,
                "investments": 0,
                "risk_profile": "modéré"
            }

            # PORTFOLIO
            rows = conn.execute(text("""
                SELECT asset, asset_type, quantity, buy_price
                FROM portfolio
                WHERE user_email=:email
            """), {"email": user_email}).fetchall()

        portfolio = []

        for r in rows:

            qty = float(r.quantity or 0)
            price = float(r.buy_price or 0)

            portfolio.append({
                "asset": r.asset,
                "type": r.asset_type,
                "value": qty * price
            })

        return compute_family_office_score(profile, portfolio)

    except Exception as e:

        return {
            "error": str(e),
            "score": 0,
            "details": {},
            "advice": []
        }
