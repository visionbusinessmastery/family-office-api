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
OPPORTUNITY_CACHE_VERSION = "v4-multi-objective-deal-flow"


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

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS opportunity_intelligence_seen (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            universe TEXT NOT NULL,
            signature TEXT NOT NULL,
            title TEXT,
            opportunity_type TEXT,
            location TEXT,
            strategy_type TEXT,
            profile_cluster TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunity_seen_unique
        ON opportunity_intelligence_seen(user_id, universe, signature)
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_opportunity_seen_recent
        ON opportunity_intelligence_seen(user_id, universe, created_at DESC)
    """))


def _safe_float(value, default=0.0):
    try:
        return float(value or default)
    except Exception:
        return default


def _stable_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def _clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def _risk_level_from_score(score: float) -> str:
    if score >= 70:
        return "low"
    if score >= 45:
        return "medium"
    return "high"


def _risk_score_from_level(level: str) -> int:
    return {"low": 82, "medium": 62, "high": 38}.get(str(level or "").lower(), 58)


def _horizon_from_strategy(strategy: str, universe: str) -> str:
    if strategy == "cashflow":
        return "short"
    if strategy == "capital_appreciation":
        return "long"
    if universe == "business":
        return "medium"
    return "medium"


def _strategy_from_item(raw: dict, universe: str, criteria: dict, index: int) -> str:
    requested = str(criteria.get("strategy") or criteria.get("ambition") or "").lower()
    title = str(raw.get("title") or "").lower()
    projection = str(raw.get("projection") or "").lower()
    combined = f"{requested} {title} {projection}"

    if any(token in combined for token in ["cashflow", "dividende", "dividend", "loyer", "rent", "side business"]):
        return "cashflow"
    if any(token in combined for token in ["valorisation", "croissance", "growth", "startup", "value"]):
        return "capital_appreciation"
    if universe == "real_estate" and index % 3 == 0:
        return "cashflow"
    if universe == "investments" and index % 3 == 1:
        return "capital_appreciation"
    return "hybrid"


def _portfolio_asset_types(profile: dict) -> set[str]:
    return {
        str(item.get("category") or "").lower()
        for item in profile.get("portfolio", [])
        if item.get("category")
    }


def _token_set(value: str) -> set[str]:
    return {
        token
        for token in str(value or "").lower().replace("/", " ").replace("-", " ").split()
        if len(token) > 2
    }


def _opportunity_signature(item: dict) -> str:
    return _stable_hash({
        "title": item.get("title"),
        "type": item.get("type"),
        "location": item.get("location"),
        "strategy_type": item.get("strategy_type"),
        "source": item.get("source"),
    })


def _profile_cluster(item: dict) -> str:
    return "|".join([
        str(item.get("universe") or ""),
        str(item.get("type") or ""),
        str(item.get("location") or ""),
        str(item.get("risk_level") or ""),
        str(item.get("investment_horizon") or ""),
        str(item.get("strategy_type") or ""),
    ]).lower()


def _similarity(first: dict, second: dict) -> float:
    if first.get("profile_cluster") and first.get("profile_cluster") == second.get("profile_cluster"):
        return 1.0

    first_tokens = _token_set(" ".join(str(first.get(key) or "") for key in ["title", "type", "location", "strategy_type"]))
    second_tokens = _token_set(" ".join(str(second.get(key) or "") for key in ["title", "type", "location", "strategy_type"]))
    if not first_tokens or not second_tokens:
        return 0.0
    return len(first_tokens & second_tokens) / max(1, len(first_tokens | second_tokens))


def _load_seen_opportunities(conn, user_id: int, universe: str, limit: int = 80) -> list[dict]:
    rows = conn.execute(text("""
        SELECT signature, title, opportunity_type, location, strategy_type, profile_cluster
        FROM opportunity_intelligence_seen
        WHERE user_id = :user_id
          AND universe = :universe
          AND created_at >= NOW() - INTERVAL '90 days'
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"user_id": user_id, "universe": universe, "limit": limit}).fetchall()

    return [
        {
            "signature": row.signature,
            "title": row.title,
            "type": row.opportunity_type,
            "location": row.location,
            "strategy_type": row.strategy_type,
            "profile_cluster": row.profile_cluster,
        }
        for row in rows
    ]


def _remember_opportunities(conn, user_id: int, universe: str, items: list[dict]):
    for item in items:
        conn.execute(text("""
            INSERT INTO opportunity_intelligence_seen
                (user_id, universe, signature, title, opportunity_type, location, strategy_type, profile_cluster, created_at)
            VALUES
                (:user_id, :universe, :signature, :title, :type, :location, :strategy_type, :profile_cluster, NOW())
            ON CONFLICT (user_id, universe, signature) DO UPDATE SET
                created_at = NOW(),
                profile_cluster = EXCLUDED.profile_cluster
        """), {
            "user_id": user_id,
            "universe": universe,
            "signature": item.get("signature"),
            "title": item.get("title"),
            "type": item.get("type"),
            "location": item.get("location"),
            "strategy_type": item.get("strategy_type"),
            "profile_cluster": item.get("profile_cluster"),
        })


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


def _deal_flow_features(raw: dict, item: dict, universe: str, index: int, criteria: dict, profile: dict) -> dict:
    location = (
        criteria.get("city")
        or criteria.get("country")
        or criteria.get("sector")
        or item.get("source")
        or "global"
    )
    strategy_type = _strategy_from_item(raw, universe, criteria, index)
    investment_horizon = _horizon_from_strategy(strategy_type, universe)
    item_type = str(item.get("type") or universe).lower()
    yield_percent = _safe_float(item.get("yield_percent"), 0)
    base_return = _potential_score(raw.get("potential")) if raw.get("potential") else item.get("ethan_score", 60)

    if yield_percent:
        return_score = _clamp((yield_percent * 9) + 28)
        expected_return = f"{round(yield_percent, 2)}% cible"
    elif universe == "business":
        return_score = _clamp(base_return + (8 if strategy_type == "cashflow" else 0))
        expected_return = "cashflow / croissance a valider"
    else:
        return_score = _clamp(base_return)
        expected_return = "potentiel relatif a confirmer"

    risk_level = str(criteria.get("risk") or raw.get("risk_level") or "").lower()
    if risk_level not in {"low", "medium", "high"}:
        if universe == "crypto" or "crypto" in item_type or strategy_type == "capital_appreciation":
            risk_level = "high"
        elif universe == "real_estate" or strategy_type == "cashflow":
            risk_level = "medium"
        else:
            risk_level = _risk_level_from_score(base_return)

    if universe == "real_estate":
        liquidity_score = 42
    elif universe == "business":
        liquidity_score = 35
    elif item_type in {"etf", "stocks", "stock", "commodities"}:
        liquidity_score = 82
    elif item_type == "crypto":
        liquidity_score = 75
    else:
        liquidity_score = 58

    owned_types = _portfolio_asset_types(profile)
    diversification_score = 86 if item_type not in owned_types else 52
    if location and str(location).lower() not in {"global", "france"}:
        diversification_score += 5

    user_risk = str(profile.get("risk_profile") or "medium").lower()
    risk_distance = abs({"low": 1, "medium": 2, "high": 3}.get(user_risk, 2) - {"low": 1, "medium": 2, "high": 3}.get(risk_level, 2))
    portfolio_fit_score = _clamp(86 - risk_distance * 20)
    if strategy_type == str(criteria.get("strategy") or criteria.get("ambition") or "").lower():
        portfolio_fit_score += 8

    momentum_score = _clamp(base_return + (10 if item.get("momentum") not in [None, "", "a confirmer"] else 0))

    return {
        "location": str(location),
        "expected_return": expected_return,
        "risk_level": risk_level,
        "investment_horizon": investment_horizon,
        "strategy_type": strategy_type,
        "return_score": _clamp(return_score),
        "risk_score": _risk_score_from_level(risk_level),
        "liquidity_score": _clamp(liquidity_score),
        "diversification_score": _clamp(diversification_score),
        "portfolio_fit_score": _clamp(portfolio_fit_score),
        "momentum_score": _clamp(momentum_score),
    }


def _score_deal_flow_item(item: dict, seen: list[dict]) -> dict:
    candidate = {
        "title": item.get("title"),
        "type": item.get("type"),
        "location": item.get("location"),
        "strategy_type": item.get("strategy_type"),
        "profile_cluster": item.get("profile_cluster"),
    }
    max_similarity = max((_similarity(candidate, past) for past in seen), default=0.0)
    novelty_score = _clamp(100 - max_similarity * 100)
    weights = {
        "return_score": 0.20,
        "risk_score": 0.15,
        "liquidity_score": 0.12,
        "diversification_score": 0.18,
        "portfolio_fit_score": 0.18,
        "momentum_score": 0.10,
        "novelty_score": 0.07,
    }
    final_score = _clamp(
        item["return_score"] * weights["return_score"]
        + item["risk_score"] * weights["risk_score"]
        + item["liquidity_score"] * weights["liquidity_score"]
        + item["diversification_score"] * weights["diversification_score"]
        + item["portfolio_fit_score"] * weights["portfolio_fit_score"]
        + item["momentum_score"] * weights["momentum_score"]
        + novelty_score * weights["novelty_score"]
    )
    breakdown = {
        "return_score": item["return_score"],
        "risk_score": item["risk_score"],
        "liquidity_score": item["liquidity_score"],
        "diversification_score": item["diversification_score"],
        "portfolio_fit_score": item["portfolio_fit_score"],
        "momentum_score": item["momentum_score"],
        "novelty_score": novelty_score,
    }
    item.update({
        "ethan_score": final_score,
        "score": {
            "final_score": final_score,
            "breakdown": breakdown,
        },
        "why_this_is_new_vs_previous": (
            "Profil distinct des dernieres opportunites analysees."
            if max_similarity < 0.45
            else "Proche d'un signal deja vu: conserve uniquement si les chiffres sont meilleurs."
        ),
    })
    return item


def _diversity_rerank(items: list[dict], max_results: int) -> list[dict]:
    selected: list[dict] = []
    used_clusters: set[str] = set()
    strategy_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}

    for item in sorted(items, key=lambda value: value.get("score", {}).get("final_score", 0), reverse=True):
        cluster = item.get("profile_cluster")
        strategy = item.get("strategy_type") or "hybrid"
        risk = item.get("risk_level") or "medium"
        too_similar = any(_similarity(item, current) > 0.72 for current in selected)

        if cluster in used_clusters or too_similar:
            continue
        if strategy_counts.get(strategy, 0) >= 2:
            continue
        if risk_counts.get(risk, 0) >= 3:
            continue

        selected.append(item)
        used_clusters.add(cluster)
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

        if len(selected) >= max_results:
            return selected

    for item in sorted(items, key=lambda value: value.get("score", {}).get("final_score", 0), reverse=True):
        if item not in selected and len(selected) < max_results:
            selected.append(item)

    return selected


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

    features = _deal_flow_features(raw, item, universe, index, criteria, profile)
    item.update(features)
    item["profile_cluster"] = _profile_cluster(item)
    item["signature"] = _opportunity_signature(item)
    item["link_or_source"] = item.get("url") or item.get("source")
    item["explanation"] = (
        f"Ethan retient ce signal pour son equilibre {item['strategy_type']} / {item['risk_level']} "
        f"et sa contribution a la diversification du portefeuille."
    )

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
        seen_opportunities = _load_seen_opportunities(conn, user_id, payload.universe)
        seen_fingerprint = _stable_hash({
            "seen": [item.get("signature") for item in seen_opportunities[:12]],
        })
        criteria_hash = _stable_hash({
            "version": OPPORTUNITY_CACHE_VERSION,
            "seen": seen_fingerprint,
            "user_id": user_id,
            "plan": profile["plan"],
            "universe": payload.universe,
            "criteria": payload.criteria,
            "portfolio": profile.get("portfolio"),
        })
        cache_payload = {
            "version": OPPORTUNITY_CACHE_VERSION,
            "seen": seen_fingerprint,
            "user_id": user_id,
            "plan": profile["plan"],
            "universe": payload.universe,
            "criteria": payload.criteria,
            "portfolio": profile.get("portfolio"),
        }
        cached = get_cached_opportunities(payload.universe, cache_payload)
        use_cached_final_selection = False

        if cached and use_cached_final_selection:
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
        scored = [
            _score_deal_flow_item(item, seen_opportunities)
            for item in normalized
            if item.get("score", {}).get("breakdown", {}).get("novelty_score", 0) >= 22
        ]
        normalized = _diversity_rerank(scored or normalized, int(depth["max_results"]))

        generated_at = datetime.utcnow().isoformat()
        result = {
            "version": OPPORTUNITY_CACHE_VERSION,
            "universe": payload.universe,
            "plan": profile["plan"],
            "depth": depth,
            "items": normalized,
            "sources": sources,
            "market_signal": market_signal,
            "generated_at": generated_at,
            "timestamp": generated_at,
            "cache_hit": False,
        }
        result["data_hash"] = _stable_hash({
            "version": result["version"],
            "universe": result["universe"],
            "plan": result["plan"],
            "items": [
                {
                    "id": item.get("id"),
                    "signature": item.get("signature"),
                    "score": item.get("score", {}).get("final_score"),
                }
                for item in normalized
            ],
            "criteria_hash": criteria_hash,
        })

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
        _remember_opportunities(conn, user_id, payload.universe, normalized)
        capture_event(
            conn,
            OPPORTUNITY_OPENED,
            user_id=user_id,
            email=email,
            properties={"universe": payload.universe, "plan": profile["plan"]},
        )
        return result
