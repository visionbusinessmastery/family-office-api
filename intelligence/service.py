

from .analyzers.allocation import allocate_portfolio
from .analyzers.ai_global import global_ai_analysis

from .analyzers.family_office_score import compute_family_office_score
from sqlalchemy import text
from database import engine


# 🔥 NORMALISATION DU RISQUE (AJOUT)
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
