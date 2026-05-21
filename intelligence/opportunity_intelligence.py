import hashlib
import json
from datetime import datetime
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from core.cache import redis_client
from database import engine
from market.service import get_market_intelligence
from analytics.analytics_events import OPPORTUNITY_OPENED
from analytics.posthog_service import capture_event
from modules.ai_business.opportunity_engine import get_ai_business_opportunities
from modules.business.opportunity_engine import get_business_opportunities
from modules.commodities.opportunity_engine import get_commodities_opportunities
from modules.crypto.opportunity_engine import get_crypto_opportunities
from modules.crowdfunding.opportunity_engine import get_crowdfunding_opportunities
from modules.etf.opportunity_engine import get_etf_opportunities
from modules.franchise.opportunity_engine import get_franchise_opportunities
from modules.private_equity.opportunity_engine import get_private_equity_opportunities
from modules.real_estate.opportunity_engine import get_real_estate_opportunities
from modules.startup.opportunity_engine import get_startup_opportunities
from modules.stocks.opportunity_engine import get_stock_opportunities
from product.entitlements import plan_allows, resolve_effective_plan
from opportunity_cache.engine import get_cached_opportunities, set_cached_opportunities


router = APIRouter()
OPPORTUNITY_CACHE_VERSION = "v3-contextual-source-links"


DISCOVERY_DEPTH = {
    "FREE": {
        "max_results": 2,
        "depth": "discovery",
        "advanced": False,
        "message": "Vue decouverte: Ethan garde les signaux simples et actionnables.",
    },
    "GOLD": {
        "max_results": 4,
        "depth": "growth",
        "advanced": True,
        "message": "Vue Growth: analyses enrichies, rendement et points de vigilance.",
    },
    "ELITE": {
        "max_results": 6,
        "depth": "strategic",
        "advanced": True,
        "message": "Vue strategique: scoring patrimonial et coherence portefeuille.",
    },
    "LIBERTY": {
        "max_results": 6,
        "depth": "global",
        "advanced": True,
        "message": "Vue globale: structuration, optimisation et opportunites internationales.",
    },
    "LEGACY": {
        "max_results": 6,
        "depth": "dynasty",
        "advanced": True,
        "message": "Vue Legacy: protection, transmission et stabilite long terme.",
    },
}


REAL_ESTATE_SOURCES = [
    "Leboncoin",
    "SeLoger",
    "Bien'ici",
    "PAP",
    "Logic-Immo",
    "Orpi",
    "Agorastore",
    "Immobilier.notaires",
    "Immo Interactif",
    "Licitor",
    "Zillow",
    "Realtor",
    "Idealista",
]

INVESTMENT_SOURCES = [
    "Market engine",
    "FMP",
    "Yahoo Finance",
    "Alpha Vantage",
    "White Rock portfolio analytics",
]

BUSINESS_SOURCES = [
    "Google Trends",
    "BPI",
    "Fusacq",
    "CRA",
    "Toute la Franchise",
    "Observatoire Franchise",
    "White Rock business modules",
]


SOURCE_HOME_URLS = {
    "Leboncoin": "https://www.leboncoin.fr/recherche",
    "SeLoger": "https://www.seloger.com",
    "Bien'ici": "https://www.bienici.com/recherche/achat",
    "PAP": "https://www.pap.fr/annonce/vente-immobiliere",
    "Logic-Immo": "https://www.logic-immo.com",
    "Orpi": "https://www.orpi.com/recherche",
    "Agorastore": "https://www.agorastore.fr",
    "Immobilier.notaires": "https://www.immobilier.notaires.fr",
    "Immo Interactif": "https://www.immo-interactif.fr",
    "Licitor": "https://www.licitor.com",
    "Zillow": "https://www.zillow.com",
    "Realtor": "https://www.realtor.com",
    "Idealista": "https://www.idealista.com",
    "Yahoo Finance": "https://finance.yahoo.com",
    "FMP": "https://financialmodelingprep.com",
    "Alpha Vantage": "https://www.alphavantage.co",
    "Market engine": "https://www.tradingview.com/markets",
    "Google Trends": "https://trends.google.com",
    "BPI": "https://bpifrance-creation.fr",
    "Fusacq": "https://www.fusacq.com",
    "CRA": "https://www.cra.asso.fr",
    "Toute la Franchise": "https://www.toute-la-franchise.com",
    "Observatoire Franchise": "https://www.observatoiredelafranchise.fr",
}


class OpportunityIntelligenceRequest(BaseModel):
    universe: str = Field(..., pattern="^(real_estate|investments|business)$")
    criteria: dict = Field(default_factory=dict)


def ensure_opportunity_intelligence_tables(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS opportunity_intelligence_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            universe TEXT NOT NULL,
            criteria_hash TEXT NOT NULL,
            plan TEXT NOT NULL DEFAULT 'FREE',
            cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_opportunity_intelligence_user_created
        ON opportunity_intelligence_requests(user_id, created_at DESC)
    """))


def _safe_float(value, default=0.0):
    try:
        return float(value or default)
    except Exception:
        return default


def _stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str):
    try:
        if redis_client:
            value = redis_client.get(key)
            return json.loads(value) if value else None
    except Exception:
        return None
    return None


def _cache_set(key: str, value: dict, ttl: int = 1800):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def _safe_market_signal(query: str, enabled: bool) -> dict:
    if not enabled:
        return {
            "query": query,
            "sentiment": "neutral",
            "sentiment_score": 50,
            "headline": None,
            "source": None,
        }

    cache_key = f"market_signal:{_stable_hash({'query': query})}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        data = get_market_intelligence(query)
        news = data.get("news") or []
        signal = {
            "query": query,
            "sentiment": data.get("sentiment", "neutral"),
            "sentiment_score": data.get("sentiment_score", 50),
            "headline": news[0].get("title") if news else None,
            "source": news[0].get("source") if news else None,
        }
    except Exception:
        signal = {
            "query": query,
            "sentiment": "neutral",
            "sentiment_score": 50,
            "headline": None,
            "source": None,
        }

    _cache_set(cache_key, signal, ttl=21600)
    return signal


def _plan_depth(plan: str) -> dict:
    if plan_allows(plan, "LEGACY"):
        return DISCOVERY_DEPTH["LEGACY"]
    if plan_allows(plan, "LIBERTY"):
        return DISCOVERY_DEPTH["LIBERTY"]
    if plan_allows(plan, "ELITE"):
        return DISCOVERY_DEPTH["ELITE"]
    if plan_allows(plan, "GOLD"):
        return DISCOVERY_DEPTH["GOLD"]
    return DISCOVERY_DEPTH["FREE"]


def _potential_score(potential: str | None) -> int:
    mapping = {
        "low": 45,
        "medium": 65,
        "stable": 68,
        "high": 82,
        "very_high": 90,
    }
    return mapping.get(str(potential or "").lower(), 62)


def _source_url(source: str, title: str, universe: str, criteria: dict) -> str:
    raw_query = " ".join(
        str(part)
        for part in [
            title,
            criteria.get("city"),
            criteria.get("country"),
            criteria.get("sector"),
            criteria.get("business_type"),
            criteria.get("strategy"),
        ]
        if part
    )
    query = quote_plus(raw_query or title or universe)

    if source == "Leboncoin":
        return f"https://www.leboncoin.fr/recherche?text={query}"
    if source == "Google Trends":
        return f"https://trends.google.com/trends/explore?q={query}"
    if source == "Yahoo Finance":
        return f"https://finance.yahoo.com/lookup?s={query}"
    if source == "TradingView" or source == "Market engine":
        return f"https://www.tradingview.com/search/?query={query}"

    return f"https://www.google.com/search?q={quote_plus(source + ' ' + raw_query)}"


def _build_user_profile(conn, user_id: int, email: str) -> dict:
    row = conn.execute(text("""
        SELECT
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.id = :user_id
    """), {"user_id": user_id}).fetchone()

    plan = resolve_effective_plan(
        row.user_plan if row else "FREE",
        row.subscription_plan if row else None,
        row.subscription_status if row else None,
    )

    finance_rows = conn.execute(text("""
        SELECT type, COALESCE(SUM(amount), 0) AS total
        FROM finance_items
        WHERE user_id = :user_id
        GROUP BY type
    """), {"user_id": user_id}).fetchall()
    finance = {item.type: _safe_float(item.total) for item in finance_rows}

    portfolio_rows = conn.execute(text("""
        SELECT category, COALESCE(SUM(quantity * purchase_price), 0) AS total, COUNT(*) AS count
        FROM portfolio
        WHERE user_id = :user_id
        GROUP BY category
    """), {"user_id": user_id}).fetchall()
    portfolio = [
        {
            "category": item.category,
            "value": _safe_float(item.total),
            "count": int(item.count or 0),
        }
        for item in portfolio_rows
    ]

    capital = sum(item["value"] for item in portfolio) + finance.get("epargne", 0)
    risk_profile = "high" if capital > 150000 else "medium" if capital > 15000 else "low"

    return {
        "email": email,
        "plan": plan,
        "level": plan,
        "score": 65 if capital > 0 else 35,
        "capital": capital,
        "savings": finance.get("epargne", 0),
        "investments": sum(item["value"] for item in portfolio),
        "risk_profile": risk_profile,
        "finance": finance,
        "portfolio": portfolio,
    }


def _normalize_item(raw: dict, universe: str, index: int, criteria: dict, profile: dict, depth: dict) -> dict:
    title = raw.get("title") or "Opportunite detectee"
    potential = raw.get("potential") or "medium"
    score = min(96, _potential_score(potential) + (8 if depth["advanced"] else 0))
    budget_label = raw.get("budget") or criteria.get("budget") or criteria.get("budget_max") or "a definir"
    location = criteria.get("city") or criteria.get("country") or criteria.get("sector") or "marche cible"

    item = {
        "id": f"{universe}-{index}",
        "universe": universe,
        "type": raw.get("type") or universe,
        "title": title,
        "description": raw.get("description") or "Signal priorise par Ethan selon ton profil et ta situation.",
        "source": raw.get("platform") or "White Rock engine",
        "url": raw.get("url") or raw.get("link"),
        "image_url": raw.get("image_url"),
        "budget": budget_label,
        "price": raw.get("price"),
        "yield_percent": raw.get("yield_percent"),
        "cashflow_estimate": raw.get("cashflow_estimate"),
        "volatility": raw.get("volatility"),
        "momentum": raw.get("momentum"),
        "ethan_score": score,
        "strengths": [
            "Coherence avec ton profil de risque",
            "Potentiel compatible avec une progression patrimoniale calme",
        ],
        "risks": [
            raw.get("risk") or "Verifier liquidite, frais et horizon avant decision",
        ],
        "projection": raw.get("projection")
        or f"Analyse {depth['depth']} sur {location}: prochaine etape, verifier chiffres reels et contraintes.",
        "next_step": "Comparer 2 alternatives, valider les frais, puis definir une action executable cette semaine.",
    }

    if universe == "real_estate":
        budget_max = _safe_float(criteria.get("budget_max"), 180000)
        budget_min = _safe_float(criteria.get("budget_min"), 0)
        target_yield = _safe_float(criteria.get("target_yield"), 5.0)
        city = criteria.get("city") or criteria.get("country") or "zone cible"
        source = raw.get("platform") or REAL_ESTATE_SOURCES[index % len(REAL_ESTATE_SOURCES)]
        price = raw.get("price") or round(budget_max * (0.82 + (index * 0.04)))
        yield_percent = raw.get("yield_percent") or round(target_yield + index * 0.35, 2)
        cashflow = raw.get("cashflow_estimate") or round((budget_max * target_yield / 100) / 12 - 450)
        item.update({
            "source": source,
            "url": item["url"] or _source_url(source, title, universe, criteria),
            "price": price,
            "yield_percent": yield_percent,
            "cashflow_estimate": cashflow,
            "strengths": [
                f"{source}: recherche ciblee sur {city} avec budget autour de {int(price):,} EUR".replace(",", " "),
                f"Rendement cible {yield_percent}% a comparer au seuil demande ({target_yield}%).",
            ],
            "risks": [
                f"Verifier tension locative et travaux a {city} avant visite.",
                "Cashflow estime a confirmer avec charges, fiscalite locale et vacance.",
            ],
            "next_step": (
                f"Ouvre {source}, filtre {city} entre {int(budget_min or 0)} et {int(budget_max)} EUR, "
                "selectionne 2 annonces comparables puis valide loyers reels, travaux et frais."
            ),
        })

    if universe == "investments":
        source = raw.get("platform") or INVESTMENT_SOURCES[index % len(INVESTMENT_SOURCES)]
        asset_type = raw.get("type") or "asset"
        volatility = raw.get("volatility") or ("moderee" if profile["risk_profile"] != "high" else "elevee")
        item.update({
            "source": source,
            "url": item["url"] or _source_url(source, title, universe, criteria),
            "yield_percent": raw.get("yield_percent") or (3.5 if raw.get("type") in ["stocks", "etf"] else None),
            "volatility": volatility,
            "momentum": raw.get("momentum") or "a confirmer",
            "strengths": [
                f"{title}: piste {asset_type} coherente avec une strategie {criteria.get('strategy', 'diversification')}.",
                f"Volatilite {volatility}: compatible avec un horizon {criteria.get('horizon', 'a definir')} si allocation limitee.",
            ],
            "risks": [
                "Verifier frais, devise et liquidite avant allocation.",
                "Limiter la concentration et comparer avec ton exposition actuelle.",
            ],
            "next_step": (
                f"Ouvre {source}, compare frais / volatilite / exposition devise, "
                "puis definis une taille de position maximale avant d'agir."
            ),
        })

    if universe == "business":
        source = raw.get("platform") or BUSINESS_SOURCES[index % len(BUSINESS_SOURCES)]
        sector = criteria.get("sector") or criteria.get("business_type") or "marche cible"
        item.update({
            "source": source,
            "url": item["url"] or _source_url(source, title, universe, criteria),
            "yield_percent": raw.get("yield_percent"),
            "strengths": [
                f"{source}: signal utile pour tester {sector} sans engagement lourd.",
                f"Potentiel {potential}: a valider avec budget {budget_label} et temps disponible.",
            ],
            "risks": [
                "Verifier marge nette, dependance operationnelle et cout d'acquisition.",
                "Eviter de lancer sans preuve de demande ou premier canal de vente.",
            ],
            "next_step": (
                f"Ouvre {source}, identifie 3 offres ou tendances comparables, "
                "puis valide une hypothese marche avec un test simple cette semaine."
            ),
        })

    return item


def _collect_real_estate(criteria: dict, profile: dict) -> list[dict]:
    base = get_real_estate_opportunities(profile)
    objective = criteria.get("objective") or "investissement locatif"
    estate_type = criteria.get("estate_type") or "ancien"
    city = criteria.get("city") or "France"

    enriched = [
        {
            "title": f"{objective.title()} - {city}",
            "type": "real_estate",
            "potential": "high",
            "budget": criteria.get("budget_max") or "medium",
            "projection": f"{estate_type.title()} avec arbitrage rendement, travaux et valorisation.",
        },
        {
            "title": f"Analyse cashflow cible - {city}",
            "type": "real_estate",
            "potential": "medium",
            "budget": criteria.get("budget_min") or "low",
            "projection": "Priorite: loyers reels, vacance, travaux et charges non recuperables.",
        },
    ]
    return enriched + base


def _collect_investments(criteria: dict, profile: dict) -> list[dict]:
    requested = {str(item).lower() for item in criteria.get("asset_classes", []) or []}
    if not requested:
        requested = {"stocks", "etf", "crypto", "commodities"}

    collected = []
    if requested & {"stocks", "actions", "dividendes", "croissance", "value"}:
        collected.extend(get_stock_opportunities(profile))
    if "etf" in requested:
        collected.extend(get_etf_opportunities(profile))
    if "crypto" in requested:
        collected.extend(get_crypto_opportunities(profile))
    if "commodities" in requested or "matieres premieres" in requested:
        collected.extend(get_commodities_opportunities(profile))

    return collected or get_stock_opportunities(profile)


def _collect_business(criteria: dict, profile: dict) -> list[dict]:
    requested = str(criteria.get("business_type") or "").lower()
    engines = []

    if not requested or "business" in requested or "digital" in requested:
        engines.extend([get_business_opportunities, get_ai_business_opportunities])
    if "startup" in requested:
        engines.append(get_startup_opportunities)
    if "franchise" in requested:
        engines.append(get_franchise_opportunities)
    if "reprise" in requested or "acquisition" in requested:
        engines.extend([get_business_opportunities, get_private_equity_opportunities])
    if "crowdfunding" in requested:
        engines.append(get_crowdfunding_opportunities)

    if not engines:
        engines = [get_business_opportunities, get_startup_opportunities, get_franchise_opportunities]

    collected = []
    for module_engine in engines:
        collected.extend(module_engine(profile))
    return collected


def _collect(universe: str, criteria: dict, profile: dict) -> tuple[list[dict], list[str]]:
    if universe == "real_estate":
        return _collect_real_estate(criteria, profile), REAL_ESTATE_SOURCES
    if universe == "investments":
        return _collect_investments(criteria, profile), INVESTMENT_SOURCES
    return _collect_business(criteria, profile), BUSINESS_SOURCES


@router.post("/opportunity-intelligence")
def get_opportunity_intelligence(
    payload: OpportunityIntelligenceRequest,
    email: str = Depends(get_current_user),
):
    with engine.begin() as conn:
        ensure_opportunity_intelligence_tables(conn)
        user_id = get_user_id(conn, email)
        if not user_id:
            raise HTTPException(status_code=404, detail="User not found")

        profile = _build_user_profile(conn, user_id, email)
        depth = _plan_depth(profile["plan"])
        criteria_hash = _stable_hash({
            "version": OPPORTUNITY_CACHE_VERSION,
            "user_id": user_id,
            "plan": profile["plan"],
            "universe": payload.universe,
            "criteria": payload.criteria,
            "portfolio": profile.get("portfolio"),
        })
        cache_payload = {
            "version": OPPORTUNITY_CACHE_VERSION,
            "user_id": user_id,
            "plan": profile["plan"],
            "universe": payload.universe,
            "criteria": payload.criteria,
            "portfolio": profile.get("portfolio"),
        }
        cached = get_cached_opportunities(payload.universe, cache_payload)

        if cached:
            conn.execute(text("""
                INSERT INTO opportunity_intelligence_requests
                    (user_id, universe, criteria_hash, plan, cache_hit)
                VALUES (:user_id, :universe, :criteria_hash, :plan, TRUE)
            """), {
                "user_id": user_id,
                "universe": payload.universe,
                "criteria_hash": criteria_hash,
                "plan": profile["plan"],
            })
            return {**cached, "cache_hit": True}

        collected, sources = _collect(payload.universe, payload.criteria, profile)
        market_signal = _safe_market_signal(
            f"{payload.universe} opportunities {payload.criteria}",
            enabled=plan_allows(profile["plan"], "GOLD"),
        )

        normalized = [
            _normalize_item(item, payload.universe, index, payload.criteria, profile, depth)
            for index, item in enumerate(collected)
            if isinstance(item, dict)
        ]
        normalized.sort(key=lambda item: item.get("ethan_score", 0), reverse=True)
        normalized = normalized[: int(depth["max_results"])]

        result = {
            "universe": payload.universe,
            "plan": profile["plan"],
            "depth": depth,
            "items": normalized,
            "sources": sources,
            "market_signal": market_signal,
            "generated_at": datetime.utcnow().isoformat(),
            "cache_hit": False,
        }

        conn.execute(text("""
            INSERT INTO opportunity_intelligence_requests
                (user_id, universe, criteria_hash, plan, cache_hit)
            VALUES (:user_id, :universe, :criteria_hash, :plan, FALSE)
        """), {
            "user_id": user_id,
            "universe": payload.universe,
            "criteria_hash": criteria_hash,
            "plan": profile["plan"],
        })

        set_cached_opportunities(payload.universe, cache_payload, result)
        capture_event(
            conn,
            OPPORTUNITY_OPENED,
            user_id=user_id,
            email=email,
            properties={"universe": payload.universe, "plan": profile["plan"]},
        )
        return result
