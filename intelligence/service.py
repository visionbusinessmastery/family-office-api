# =========================
# IMPORTS
# =========================
from .analyzers.allocation import allocate_portfolio
from .analyzers.ai_global import global_ai_analysis

from .analyzers.family_office_score import compute_family_office_score
from sqlalchemy import text
from database import engine

# =========================
# NORMALISATION DU RISQUE
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
# GET GLOBAL INTELLIGENCE
# =========================
def get_global_intelligence(query):

    try:
        # 🔥 FIX ICI
        risk = normalize_risk(query.risk)

        # 🔹 REAL ESTATE
        real_data = get_real_estate_intelligence(query.city, query.budget)

        # 🔹 CRYPTO
        crypto_data = get_crypto_intelligence(
            type("obj", (), {
                "symbol": "BTC",
                "strategy": "long_term"
            })
        )

        # 🔹 STOCKS
        stock_data = get_stock_intelligence(
            type("obj", (), {
                "symbol": "AAPL",
                "strategy": "long_term"
            })
        )

        # 🔥 on passe le bon risk
        query.risk = risk

        allocation = allocate_portfolio(query, real_data, crypto_data, stock_data)

        ai = global_ai_analysis({
            "budget": query.budget,
            "risk": risk,
            "allocation": allocation
        })

        return {
            "real_estate": real_data[:3] if isinstance(real_data, list) else [],
            "crypto": crypto_data,
            "stocks": stock_data,
            "allocation": allocation,
            "ai_global": ai
        }

    except Exception as e:
        return {
            "error": str(e)
        }


# =========================
# GET USER FINANCIAL OVERVIEW
# =========================
def get_user_financial_overview(user_id):

    try:

        # =========================
        # INCOME SOURCES
        # =========================
        with engine.connect() as conn:
            income_rows = conn.execute(text("""
                SELECT name, income_type, monthly_income
                FROM income_sources
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

        income_sources = []
        total_income = 0

        for r in income_rows:
            income_sources.append({
                "name": r.name,
                "type": r.income_type,
                "monthly_income": float(r.monthly_income or 0)
            })

            total_income += float(r.monthly_income or 0)

        # =========================
        # DEBTS
        # =========================
        with engine.connect() as conn:
            debt_rows = conn.execute(text("""
                SELECT name, debt_type, remaining_amount, monthly_payment
                FROM debts
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

        debts = []
        total_debt = 0
        total_monthly_debt = 0

        for r in debt_rows:
            debts.append({
                "name": r.name,
                "type": r.debt_type,
                "remaining_amount": float(r.remaining_amount or 0),
                "monthly_payment": float(r.monthly_payment or 0)
            })

            total_debt += float(r.remaining_amount or 0)
            total_monthly_debt += float(r.monthly_payment or 0)

        # =========================
        # SAVINGS
        # =========================
        with engine.connect() as conn:
            savings_rows = conn.execute(text("""
                SELECT name, bank, balance, currency
                FROM savings_accounts
                WHERE user_id=:uid
            """), {"uid": user_id}).fetchall()

        savings = []
        total_savings = 0

        for r in savings_rows:
            savings.append({
                "name": r.name,
                "bank": r.bank,
                "balance": float(r.balance or 0),
                "currency": r.currency
            })

            total_savings += float(r.balance or 0)

        # =========================
        # KPI CALCULS (IMPORTANT)
        # =========================
        net_cashflow = total_income - total_monthly_debt

        net_worth_estimate = total_savings - total_debt

        savings_rate = (total_savings / total_income * 100) if total_income > 0 else 0

        debt_ratio = (total_debt / (total_savings + 1)) * 100

        # =========================
        # RETURN STRUCTURE (LIKE YOUR STYLE)
        # =========================
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
                "net_worth_estimate": round(net_worth_estimate, 2),

                "savings_rate": round(savings_rate, 2),
                "debt_ratio": round(debt_ratio, 2)
            }
        }

    except Exception as e:
        return {
            "error": str(e)
        }
        


# =========================
# GET FAMILY OFFICE SCORE
# =========================
def get_family_office_score(user_email):

    # =========================
    # PROFILE
    # =========================
    with engine.connect() as conn:
        profile_row = conn.execute(text("""
            SELECT savings, investments, risk_profile
            FROM user_profiles
            WHERE user_email=:email
        """), {"email": user_email}).fetchone()

    profile = dict(profile_row._mapping) if profile_row else {}

    # =========================
    # PORTFOLIO
    # =========================
    portfolio = []

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT asset, asset_type, quantity, buy_price
            FROM portfolio
            WHERE user_email=:email
        """), {"email": user_email}).fetchall()

    for r in rows:
        value = r[2] * r[3]

        portfolio.append({
            "asset": r[0],
            "type": r[1],
            "value": value
        })

    # =========================
    # SCORE
    # =========================
    return compute_family_office_score(profile, portfolio)
