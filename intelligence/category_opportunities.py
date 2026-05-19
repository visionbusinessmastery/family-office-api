from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine
from market.service import get_market_intelligence
from modules.ai_business.opportunity_engine import get_ai_business_opportunities
from modules.business.opportunity_engine import get_business_opportunities
from modules.crowdfunding.opportunity_engine import get_crowdfunding_opportunities
from modules.franchise.opportunity_engine import get_franchise_opportunities
from modules.private_equity.opportunity_engine import get_private_equity_opportunities
from modules.real_estate.opportunity_engine import get_real_estate_opportunities
from modules.startup.opportunity_engine import get_startup_opportunities
from modules.stocks.opportunity_engine import get_stock_opportunities
from portfolio.real_estate_routes import ensure_real_estate_table
from portfolio.specialized_assets_routes import ensure_venture_table, ensure_yield_table


router = APIRouter()


def safe_market(query: str):
    try:
        data = get_market_intelligence(query)
        news = data.get("news") or []
        return {
            "query": query,
            "sentiment": data.get("sentiment", "neutral"),
            "sentiment_score": data.get("sentiment_score", 50),
            "headline": news[0].get("title") if news else None,
            "source": news[0].get("source") if news else None,
        }
    except Exception:
        return {
            "query": query,
            "sentiment": "neutral",
            "sentiment_score": 50,
            "headline": None,
            "source": None,
        }


def first_opportunity(items):
    if not items:
        return None

    item = items[0]
    return {
        "title": item.get("title", "Opportunite detectee"),
        "type": item.get("type"),
        "risk": item.get("risk"),
        "potential": item.get("potential"),
        "platform": item.get("platform"),
    }


def build_profile(conn, user_id: int):
    finance = conn.execute(text("""
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM finance_items
        WHERE user_id = :user_id
        GROUP BY type
    """), {"user_id": user_id}).fetchall()
    totals = {row.type: float(row.total or 0) for row in finance}

    portfolio_value = conn.execute(text("""
        SELECT COALESCE(SUM(quantity * purchase_price), 0)
        FROM portfolio
        WHERE user_id = :user_id
    """), {"user_id": user_id}).scalar()

    return {
        "score": 60,
        "capital": float(portfolio_value or 0) + totals.get("epargne", 0),
        "risk_profile": "medium",
        "level": "FREE",
        "finance": totals,
    }


def category_payload(title, key, count, analysis, quick_action, opportunity, market):
    return {
        "key": key,
        "title": title,
        "count": count,
        "analysis": analysis,
        "quick_action": quick_action,
        "detected_opportunity": opportunity,
        "market_signal": market,
    }


@router.get("/category-opportunities")
def get_category_opportunities(user=Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = get_user_id(conn, user)

        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        profile = build_profile(conn, user_id)
        results = []

        portfolio_rows = conn.execute(text("""
            SELECT category, COUNT(*) AS count, COALESCE(SUM(quantity * purchase_price), 0) AS total
            FROM portfolio
            WHERE user_id = :user_id
            GROUP BY category
        """), {"user_id": user_id}).fetchall()

        for row in portfolio_rows:
            category = (row.category or "AUTRE").upper()
            if category in ["STOCK", "STOCKS", "ETF", "CRYPTO", "COMMODITIES", "FOREX"]:
                engine_items = get_stock_opportunities(profile)
                quick_action = (
                    "Verifier que l'exposition devise reste coherente avec tes revenus et depenses."
                    if category == "FOREX"
                    else "Verifier si une seule ligne depasse 30% de cette poche."
                )
                results.append(category_payload(
                    title=category.replace("_", " "),
                    key=category.lower(),
                    count=int(row.count or 0),
                    analysis=(
                        f"Cette poche represente {round(float(row.total or 0), 2)} EUR. "
                        "Ethan surveille surtout concentration, volatilite et liquidite."
                    ),
                    quick_action=quick_action,
                    opportunity=first_opportunity(engine_items),
                    market=safe_market(category),
                ))

        ensure_real_estate_table(conn)
        real_estate_rows = conn.execute(text("""
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(purchase_price), 0) AS invested,
                COALESCE(SUM(CASE WHEN estimated_value > 0 THEN estimated_value ELSE purchase_price END), 0) AS value
            FROM real_estate_assets
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()

        if real_estate_rows and int(real_estate_rows.count or 0) > 0:
            gain = float(real_estate_rows.value or 0) - float(real_estate_rows.invested or 0)
            results.append(category_payload(
                title="Immobilier",
                key="real_estate",
                count=int(real_estate_rows.count or 0),
                analysis=(
                    f"Plus-value latente estimee: {round(gain, 2)} EUR. "
                    "Ethan compare rendement, liquidite et potentiel de revente."
                ),
                quick_action="Mettre a jour la valeur estimee avec un prix de marche recent.",
                opportunity=first_opportunity(get_real_estate_opportunities(profile)),
                market=safe_market("immobilier investissement rendement"),
            ))

        ensure_yield_table(conn)
        yield_rows = conn.execute(text("""
            SELECT asset_type, COUNT(*) AS count, COALESCE(AVG(average_rate), 0) AS rate
            FROM yield_assets
            WHERE user_id = :user_id
            GROUP BY asset_type
        """), {"user_id": user_id}).fetchall()

        for row in yield_rows:
            asset_type = row.asset_type
            is_private = asset_type == "private_equity"
            results.append(category_payload(
                title="Private Equity" if is_private else "Crowdfunding",
                key=asset_type,
                count=int(row.count or 0),
                analysis=(
                    f"Taux moyen renseigne: {round(float(row.rate or 0), 2)}%. "
                    "Ethan arbitre rendement attendu, duree de blocage et risque de defaut."
                ),
                quick_action="Verifier les garanties, la duree et la part maximale par dossier.",
                opportunity=first_opportunity(
                    get_private_equity_opportunities(profile)
                    if is_private
                    else get_crowdfunding_opportunities(profile)
                ),
                market=safe_market("private equity investment" if is_private else "crowdfunding immobilier"),
            ))

        ensure_venture_table(conn)
        venture_rows = conn.execute(text("""
            SELECT asset_type, COUNT(*) AS count, COALESCE(SUM(revenue - charges), 0) AS result
            FROM venture_assets
            WHERE user_id = :user_id
            GROUP BY asset_type
        """), {"user_id": user_id}).fetchall()

        engines = {
            "ai_business": get_ai_business_opportunities,
            "business": get_business_opportunities,
            "startup": get_startup_opportunities,
            "franchise": get_franchise_opportunities,
        }

        for row in venture_rows:
            asset_type = row.asset_type
            label = asset_type.replace("_", " ").title()
            results.append(category_payload(
                title=label,
                key=asset_type,
                count=int(row.count or 0),
                analysis=(
                    f"Resultat cumule: {round(float(row.result or 0), 2)} EUR. "
                    "Ethan priorise marge, dette, levee et valorisation."
                ),
                quick_action="Identifier une action qui augmente le resultat dans les 30 prochains jours.",
                opportunity=first_opportunity(engines.get(asset_type, get_business_opportunities)(profile)),
                market=safe_market(label),
            ))

    return {"categories": results}
