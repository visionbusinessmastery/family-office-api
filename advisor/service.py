import hashlib
import json
import os
from datetime import date

from openai import OpenAI
from sqlalchemy import text

from advisor.autopilot_v4_engine import get_autopilot_v4
from auth.utils import get_user_id
from core.cache import redis_client
from database import engine
from portfolio.service import get_user_portfolio
from product.entitlements import normalize_plan, plan_allows, resolve_effective_plan
from advisor.user_state import centralized_user_state_builder


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None
_ethan_schema_ready = False
ADVISOR_CACHE_VERSION = "v4-question-aware-fallback"

MODEL_LIGHT = os.getenv("ETHAN_MODEL_LIGHT", "gpt-5-nano")
MODEL_STANDARD = os.getenv("ETHAN_MODEL_STANDARD", "gpt-5-mini")
MODEL_PREMIUM = os.getenv("ETHAN_MODEL_PREMIUM", "gpt-5")
MODEL_DYNASTY = os.getenv("ETHAN_MODEL_DYNASTY", MODEL_PREMIUM)
MODEL_FALLBACK = os.getenv("ETHAN_MODEL_FALLBACK", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

ESTIMATED_INPUT_COST = {
    MODEL_LIGHT: float(os.getenv("ETHAN_LIGHT_INPUT_COST_PER_1M", "0.05")),
    MODEL_STANDARD: float(os.getenv("ETHAN_STANDARD_INPUT_COST_PER_1M", "0.25")),
    MODEL_PREMIUM: float(os.getenv("ETHAN_PREMIUM_INPUT_COST_PER_1M", "1.25")),
    MODEL_DYNASTY: float(os.getenv("ETHAN_DYNASTY_INPUT_COST_PER_1M", "1.25")),
}

ESTIMATED_OUTPUT_COST = {
    MODEL_LIGHT: float(os.getenv("ETHAN_LIGHT_OUTPUT_COST_PER_1M", "0.4")),
    MODEL_STANDARD: float(os.getenv("ETHAN_STANDARD_OUTPUT_COST_PER_1M", "2.0")),
    MODEL_PREMIUM: float(os.getenv("ETHAN_PREMIUM_OUTPUT_COST_PER_1M", "10.0")),
    MODEL_DYNASTY: float(os.getenv("ETHAN_DYNASTY_OUTPUT_COST_PER_1M", "10.0")),
}

PLAN_CONFIG = {
    "FREE": {
        "tier": "ESSENTIALS",
        "max_output_tokens": 220,
        "daily_deep_sessions": 0,
        "default_model": MODEL_LIGHT,
    },
    "GOLD": {
        "tier": "GROWTH",
        "max_output_tokens": 420,
        "daily_deep_sessions": 1,
        "default_model": MODEL_STANDARD,
    },
    "ELITE": {
        "tier": "STRATEGIST",
        "max_output_tokens": 650,
        "daily_deep_sessions": 3,
        "default_model": MODEL_STANDARD,
    },
    "LIBERTY": {
        "tier": "EXECUTIVE",
        "max_output_tokens": 800,
        "daily_deep_sessions": 6,
        "default_model": MODEL_PREMIUM,
    },
    "LEGACY": {
        "tier": "DYNASTY",
        "max_output_tokens": 900,
        "daily_deep_sessions": 10,
        "default_model": MODEL_DYNASTY,
    },
}

LOW_KEYWORDS = [
    "bonjour",
    "merci",
    "resume",
    "rappel",
    "motivation",
    "simple",
    "rapide",
    "action du jour",
]

MEDIUM_KEYWORDS = [
    "portfolio",
    "portefeuille",
    "budget",
    "diversification",
    "immobilier",
    "crypto",
    "etf",
    "forex",
    "opportunite",
    "capital",
]

HIGH_KEYWORDS = [
    "fiscal",
    "trust",
    "holding",
    "succession",
    "transmission",
    "gouvernance",
    "legacy",
    "heritage",
    "simulation",
    "architecture patrimoniale",
    "strategie internationale",
]


def ensure_ethan_ai_tables(conn):
    global _ethan_schema_ready

    if _ethan_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_memory (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            strategic_summary TEXT,
            session_summary TEXT,
            last_topic TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ethan_usage_events (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            email TEXT,
            plan TEXT,
            tier TEXT,
            task_type TEXT,
            complexity TEXT,
            model TEXT,
            cache_hit BOOLEAN DEFAULT FALSE,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            estimated_cost_usd NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ethan_usage_events_user_day_idx
        ON ethan_usage_events(user_id, created_at)
    """))

    _ethan_schema_ready = True


def get_cache(key):
    try:
        if redis_client:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(key, value, ttl=300):
    try:
        if redis_client:
            redis_client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def estimate_tokens(text_value):
    return max(1, int(len(text_value or "") / 4))


def estimate_cost(model, input_tokens, output_tokens):
    input_cost = ESTIMATED_INPUT_COST.get(model, ESTIMATED_INPUT_COST.get(MODEL_STANDARD, 0))
    output_cost = ESTIMATED_OUTPUT_COST.get(model, ESTIMATED_OUTPUT_COST.get(MODEL_STANDARD, 0))
    return round((input_tokens / 1_000_000) * input_cost + (output_tokens / 1_000_000) * output_cost, 8)


def classify_request(message):
    normalized = (message or "").lower()

    if any(keyword in normalized for keyword in HIGH_KEYWORDS):
        return "high"

    if len(normalized) > 420:
        return "high"

    if any(keyword in normalized for keyword in MEDIUM_KEYWORDS):
        return "medium"

    if len(normalized) < 160 or any(keyword in normalized for keyword in LOW_KEYWORDS):
        return "low"

    return "medium"


def classify_task(message, complexity):
    normalized = (message or "").lower()

    if complexity == "high":
        return "strategic_analysis"
    if any(word in normalized for word in ["portfolio", "portefeuille", "allocation", "diversification"]):
        return "portfolio_guidance"
    if any(word in normalized for word in ["budget", "charge", "revenu", "cashflow"]):
        return "financial_guidance"
    if any(word in normalized for word in ["succession", "heritage", "legacy", "transmission"]):
        return "legacy_guidance"
    return "conversation"


def get_user_plan(conn, email):
    row = conn.execute(text("""
        SELECT
            users.id,
            users.plan AS user_plan,
            subscriptions.plan AS subscription_plan,
            subscriptions.status AS subscription_status
        FROM users
        LEFT JOIN subscriptions ON subscriptions.user_id = users.id
        WHERE users.email = :email
    """), {"email": email}).fetchone()

    if not row:
        return None, "FREE"

    return row.id, resolve_effective_plan(
        row.user_plan,
        row.subscription_plan,
        row.subscription_status,
    )


def get_daily_deep_usage(conn, user_id):
    if not user_id:
        return 0

    return int(conn.execute(text("""
        SELECT COUNT(*)
        FROM ethan_usage_events
        WHERE user_id = :user_id
          AND complexity = 'high'
          AND cache_hit = FALSE
          AND created_at::date = CURRENT_DATE
    """), {"user_id": user_id}).scalar() or 0)


def choose_model(plan, complexity, deep_sessions_used):
    normalized_plan = normalize_plan(plan)
    config = PLAN_CONFIG[normalized_plan]
    soft_budget_active = False

    if complexity == "low":
        model = MODEL_LIGHT
    elif complexity == "medium":
        model = MODEL_STANDARD
    else:
        if config["daily_deep_sessions"] <= deep_sessions_used:
            model = MODEL_STANDARD if plan_allows(normalized_plan, "GOLD") else MODEL_LIGHT
            soft_budget_active = True
        elif plan_allows(normalized_plan, "LIBERTY"):
            model = config["default_model"]
        elif plan_allows(normalized_plan, "ELITE"):
            model = MODEL_PREMIUM
        else:
            model = MODEL_STANDARD

    return model, soft_budget_active


def compact_context(context):
    score = context.get("global_score") or context.get("score") or 0
    if isinstance(score, dict):
        score = score.get("score", 0)

    data_profile = context.get("data_profile") or {}
    financial = context.get("financial_features") or {}
    opportunities = context.get("opportunities") or {}
    opportunity_count = (
        len(opportunities)
        if isinstance(opportunities, list)
        else opportunities.get("count", 0)
        if isinstance(opportunities, dict)
        else 0
    )

    return {
        "score": score,
        "level": context.get("level"),
        "plan": context.get("plan"),
        "status": context.get("state", "READY"),
        "opportunity_count": opportunity_count,
        "completion_percent": data_profile.get("completion_percent"),
        "cashflow": financial.get("cashflow_score"),
        "debt_risk": financial.get("debt_risk_score"),
        "savings_velocity": financial.get("savings_velocity_score"),
        "top_advice": (context.get("advice") or [])[:3],
    }


def compact_portfolio(portfolio):
    assets = portfolio.get("portfolio") if isinstance(portfolio, dict) else portfolio
    if not isinstance(assets, list):
        assets = portfolio.get("assets", []) if isinstance(portfolio, dict) else []

    total_value = 0
    exposures = {}
    top_assets = []

    for asset in assets[:80]:
        name = asset.get("asset_name") or asset.get("name") or "Asset"
        category = (asset.get("asset_type") or asset.get("category") or asset.get("type") or "OTHER").upper()
        value = float(asset.get("value") or asset.get("current_value") or 0)
        if not value:
            qty = float(asset.get("quantity") or 0)
            price = float(asset.get("current_price") or asset.get("purchase_price") or 0)
            value = qty * price

        total_value += value
        exposures[category] = exposures.get(category, 0) + value
        top_assets.append({"name": name, "category": category, "value": round(value, 2)})

    top_assets = sorted(top_assets, key=lambda item: item["value"], reverse=True)[:5]

    return {
        "asset_count": len(assets),
        "total_value": round(total_value, 2),
        "exposures": dict(sorted(exposures.items(), key=lambda item: item[1], reverse=True)[:6]),
        "top_assets": top_assets,
    }


def get_memory(conn, user_id):
    if not user_id:
        return {}

    row = conn.execute(text("""
        SELECT strategic_summary, session_summary, last_topic
        FROM ethan_memory
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        return {}

    return {
        "strategic_summary": row.strategic_summary,
        "session_summary": row.session_summary,
        "last_topic": row.last_topic,
    }


def update_memory(conn, user_id, message, answer, context):
    if not user_id:
        return

    topic = classify_task(message, classify_request(message))
    score = get_context_score(context)
    answer_excerpt = (answer or "")[:500]
    session_summary = (
        f"Derniere question: {message[:220]} | "
        f"Orientation Ethan: {answer_excerpt}"
    )
    strategic_summary = (
        f"Score {score}/100. Plan {context.get('plan', 'FREE')}. "
        f"Niveau {context.get('level', 'non precise')}."
    )

    conn.execute(text("""
        INSERT INTO ethan_memory (
            user_id, strategic_summary, session_summary, last_topic, updated_at
        )
        VALUES (
            :user_id, :strategic_summary, :session_summary, :last_topic, NOW()
        )
        ON CONFLICT (user_id)
        DO UPDATE SET
            strategic_summary = EXCLUDED.strategic_summary,
            session_summary = EXCLUDED.session_summary,
            last_topic = EXCLUDED.last_topic,
            updated_at = NOW()
    """), {
        "user_id": user_id,
        "strategic_summary": strategic_summary,
        "session_summary": session_summary,
        "last_topic": topic,
    })


def record_usage(
    conn,
    user_id,
    email,
    plan,
    tier,
    task_type,
    complexity,
    model,
    cache_hit,
    input_tokens=0,
    output_tokens=0,
):
    conn.execute(text("""
        INSERT INTO ethan_usage_events (
            user_id, email, plan, tier, task_type, complexity, model, cache_hit,
            input_tokens, output_tokens, estimated_cost_usd
        )
        VALUES (
            :user_id, :email, :plan, :tier, :task_type, :complexity, :model,
            :cache_hit, :input_tokens, :output_tokens, :estimated_cost_usd
        )
    """), {
        "user_id": user_id,
        "email": email,
        "plan": plan,
        "tier": tier,
        "task_type": task_type,
        "complexity": complexity,
        "model": model,
        "cache_hit": cache_hit,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": estimate_cost(model, input_tokens, output_tokens),
    })


def build_advisor_messages(context, portfolio, opportunities, memory, message, plan, tier, complexity):
    system_prompt = (
        "Tu es ETHAN, Conseiller patrimonial WHITE ROCK. "
        "Style: calme, premium, concis, humain, strategique. "
        "Ne mentionne jamais les couts API, les tokens, OpenAI, ni l'optimisation technique. "
        "Reponds en francais simple. Pas de conseil fiscal/legal definitif: propose de verifier avec un professionnel. "
        "Structure courte: diagnostic, action prioritaire, point de vigilance."
    )

    compressed_context = {
        "ethan_tier": tier,
        "plan": plan,
        "complexity": complexity,
        "profile": compact_context(context),
        "portfolio": compact_portfolio(portfolio),
        "opportunities": opportunities[:3] if isinstance(opportunities, list) else opportunities,
        "memory": memory,
    }

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Contexte compresse WHITE ROCK:\n"
                f"{json.dumps(compressed_context, separators=(',', ':'), ensure_ascii=False)}\n\n"
                f"Question utilisateur: {message}"
            ),
        },
    ]


def get_llm_response(messages, model, max_output_tokens):
    prompt_hash = stable_hash({"messages": messages, "model": model, "max": max_output_tokens})
    llm_cache_key = f"llm:{prompt_hash}"

    cached = get_cache(llm_cache_key)
    if cached:
        return cached, True, estimate_tokens(json.dumps(messages)), estimate_tokens(cached), model

    if not client:
        return None, False, estimate_tokens(json.dumps(messages)), 0, model

    def _call(selected_model, token_param="max_completion_tokens"):
        kwargs = {
            "model": selected_model,
            "messages": messages,
            token_param: max_output_tokens,
        }
        return client.chat.completions.create(**kwargs)

    response = None

    try:
        response = _call(model)
    except Exception:
        try:
            response = _call(MODEL_FALLBACK)
            model = MODEL_FALLBACK
        except Exception:
            try:
                response = _call(MODEL_FALLBACK, "max_tokens")
                model = MODEL_FALLBACK
            except Exception:
                return None, False, estimate_tokens(json.dumps(messages)), 0, model

    try:
        llm_text = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) or estimate_tokens(json.dumps(messages))
        output_tokens = getattr(usage, "completion_tokens", None) or estimate_tokens(llm_text)
        set_cache(llm_cache_key, llm_text, ttl=1800)
        return llm_text, False, input_tokens, output_tokens, model
    except Exception:
        return None, False, estimate_tokens(json.dumps(messages)), 0, model


def build_hash(user_email, message, plan, complexity, fingerprint):
    raw = {
        "version": ADVISOR_CACHE_VERSION,
        "email": user_email,
        "message": message.strip().lower(),
        "plan": plan,
        "complexity": complexity,
        "fingerprint": fingerprint,
    }
    return stable_hash(raw)


def advisor_logic(user_email, message, level=None):
    with engine.begin() as conn:
        ensure_ethan_ai_tables(conn)
        unified_state = centralized_user_state_builder(conn, user_email)
        user_id = unified_state["user_id"]
        plan = unified_state["plan"]
        config = PLAN_CONFIG[plan]
        tier = config["tier"]
        complexity = classify_request(message)
        task_type = classify_task(message, complexity)
        deep_sessions_used = get_daily_deep_usage(conn, user_id)
        model, soft_budget_active = choose_model(plan, complexity, deep_sessions_used)

        context = unified_state["dashboard_context"]
        portfolio = unified_state["portfolio"]
        opportunities = unified_state["opportunities"]
        memory = get_memory(conn, user_id)

        fingerprint = stable_hash({
            "version": ADVISOR_CACHE_VERSION,
            "score": unified_state.get("score"),
            "context": compact_context(context),
            "portfolio": compact_portfolio(portfolio),
            "opportunity_count": (
                opportunities.get("count", 0)
                if isinstance(opportunities, dict)
                else len(opportunities)
                if isinstance(opportunities, list)
                else 0
            ),
            "memory": memory,
        })[:16]
        cache_key = f"advisor:{build_hash(user_email, message, plan, complexity, fingerprint)}"

        cached = get_cache(cache_key)
        if cached:
            record_usage(conn, user_id, user_email, plan, tier, task_type, complexity, model, True)
            cached["cache_hit"] = True
            return cached

        messages = build_advisor_messages(
            context=context,
            portfolio=portfolio,
            opportunities=opportunities,
            memory=memory,
            message=message,
            plan=plan,
            tier=tier,
            complexity=complexity,
        )

        llm_text, llm_cache_hit, input_tokens, output_tokens, actual_model = get_llm_response(
            messages,
            model,
            config["max_output_tokens"],
        )

        if not llm_text:
            result = build_fallback_response(
                context,
                opportunities,
                tier,
                message=message,
                portfolio=portfolio,
            )
            record_usage(conn, user_id, user_email, plan, tier, task_type, complexity, actual_model, False, input_tokens, 0)
            set_cache(cache_key, result, ttl=180)
            return result

        update_memory(conn, user_id, message, llm_text, context)
        record_usage(
            conn,
            user_id,
            user_email,
            plan,
            tier,
            task_type,
            complexity,
            actual_model,
            llm_cache_hit,
            input_tokens,
            output_tokens,
        )

        result = {
            "analysis": llm_text,
            "context_score": get_context_score(context),
            "tier": tier,
            "complexity": complexity,
            "soft_budget_active": soft_budget_active,
            "cache_hit": llm_cache_hit,
            "autopilot": run_autopilot_safely(
                user_email=user_email,
                portfolio=compact_portfolio(portfolio),
                market={},
                context=compact_context(context),
                llm_text=llm_text[:900],
                level=plan,
            ) if complexity == "high" and plan_allows(plan, "ELITE") else None,
        }

        set_cache(cache_key, result, ttl=900 if complexity != "high" else 300)
        return result


def run_autopilot_safely(user_email, portfolio, market, context, llm_text, level):
    try:
        autopilot = get_autopilot_v4()
        return autopilot.run(
            user_email=user_email,
            portfolio=portfolio,
            market=market,
            context=context,
            llm_analysis=llm_text,
            level=level,
        )
    except Exception as e:
        return {"status": "unavailable", "message": str(e)}


def get_context_score(context):
    score = context.get("global_score") or context.get("score", 0)

    if isinstance(score, dict):
        return score.get("score", 0)

    return score


def build_fallback_response(context, opportunities, tier="ESSENTIALS"):
    score = get_context_score(context)
    opportunity_count = (
        len(opportunities)
        if isinstance(opportunities, list)
        else opportunities.get("count", 0)
        if isinstance(opportunities, dict)
        else 0
    )

    return {
        "analysis": (
            f"Je garde une lecture simple: ton score est {score}/100 et "
            f"{opportunity_count} opportunité(s) ressortent. "
            "Action prioritaire: clarifie le cashflow disponible, reduis la plus forte "
            "concentration, puis réinvestis progressivement dans la poche la mieux maîtrisée."
        ),
        "context_score": score,
        "tier": tier,
        "autopilot": None,
    }


def _fallback_focus(message: str) -> str:
    normalized = (message or "").lower()
    if any(word in normalized for word in ["immobilier", "residence", "locatif", "loyer", "travaux"]):
        return "real_estate"
    if any(word in normalized for word in ["opportunite", "opportunites", "deal", "signal", "source"]):
        return "opportunities"
    if any(word in normalized for word in ["cashflow", "revenu", "charge", "epargne", "budget"]):
        return "cashflow"
    if any(word in normalized for word in ["risque", "concentration", "exposition", "diversification"]):
        return "risk"
    if any(word in normalized for word in ["portfolio", "portefeuille", "action", "etf", "crypto", "forex"]):
        return "portfolio"
    if any(word in normalized for word in ["business", "entreprise", "startup", "franchise", "reprise"]):
        return "business"
    if any(word in normalized for word in ["legacy", "heritage", "transmission", "famille", "gouvernance"]):
        return "legacy"
    if any(word in normalized for word in ["score", "progression", "xp", "badge", "mission"]):
        return "progression"
    return "general"


def _opportunity_count(opportunities) -> int:
    return (
        len(opportunities)
        if isinstance(opportunities, list)
        else opportunities.get("count", 0)
        if isinstance(opportunities, dict)
        else 0
    )


def _top_portfolio_exposure(portfolio) -> str:
    compact = compact_portfolio(portfolio)
    exposures = compact.get("exposures") or {}
    if not exposures:
        return "aucune poche dominante encore visible"

    top_name, top_value = next(iter(exposures.items()))
    total = compact.get("total_value") or 0
    share = round((float(top_value or 0) / float(total or 1)) * 100)
    return f"{top_name} ({share}% environ)"


def build_fallback_response(context, opportunities, tier="ESSENTIALS", message=None, portfolio=None):
    score = get_context_score(context)
    opportunity_count = _opportunity_count(opportunities)
    focus = _fallback_focus(message or "")
    top_exposure = _top_portfolio_exposure(portfolio or {})

    responses = {
        "real_estate": (
            f"Sur l'immobilier, je pars de ton score {score}/100. "
            "Priorite: rendement net, travaux, vacance locative et fiscalite locale avant de comparer les annonces. "
            "Action simple: selectionne 2 biens similaires dans la meme zone, puis calcule le cashflow net avec charges et marge de securite."
        ),
        "opportunities": (
            f"Je vois {opportunity_count} opportunite(s) dans le moteur. Ne les traite pas comme une liste a suivre aveuglement: "
            "classe-les par strategie cashflow, valorisation et diversification, puis garde seulement celles qui reduisent une faiblesse actuelle. "
            "Action utile: ouvre la meilleure source, compare 2 alternatives et note pourquoi elle est vraiment nouvelle pour ton portefeuille."
        ),
        "cashflow": (
            f"Pour le cashflow, ton score {score}/100 indique qu'il faut d'abord clarifier la capacite mensuelle disponible. "
            "Priorite: revenus recurrents, charges fixes, epargne automatique, puis marge de securite. "
            "Action simple: isole le montant investissable mensuel prudent avant toute nouvelle allocation."
        ),
        "risk": (
            f"Le point de risque principal semble etre la concentration: ta poche dominante est {top_exposure}. "
            "Priorite: ne pas ajouter une opportunite qui renforce cette concentration, meme si elle parait attractive. "
            "Action utile: fixe une limite par classe d'actifs puis cherche une opportunite qui apporte une vraie diversification."
        ),
        "portfolio": (
            f"Pour le portefeuille, je regarderais d'abord l'allocation plutot que le prochain actif. Ta poche la plus visible est {top_exposure}. "
            "Action simple: compare chaque nouvelle position a son role exact: stabiliser, diversifier, produire du cashflow ou chercher de la valorisation."
        ),
        "business": (
            "Sur le business, je privilegie une lecture tres terrain: marge nette, temps disponible, canal d'acquisition et dependance operationnelle. "
            "Action simple: choisis une seule piste, teste la demande avec une offre minimale, puis decide seulement apres un premier signal concret."
        ),
        "legacy": (
            "Pour la partie Legacy, l'objectif n'est pas d'aller vite mais de rendre le patrimoine plus transmissible et moins dependant de toi. "
            "Action simple: clarifie beneficiaires, documents essentiels, roles familiaux et risques de concentration avant toute optimisation avancee."
        ),
        "progression": (
            f"Pour faire progresser ton score {score}/100, l'action la plus rentable est souvent la donnee manquante la plus simple. "
            "Priorite: completer cashflow, objectifs, horizon, puis documenter les actifs majeurs. "
            "Action utile: choisis une mission concrete et mesurable aujourd'hui plutot qu'une grande refonte."
        ),
        "general": (
            f"Je garde une lecture simple: ton score est {score}/100 et {opportunity_count} opportunite(s) ressortent. "
            "Pour te repondre plus precisement, je partirais de trois axes: cashflow disponible, concentration actuelle, puis opportunite qui apporte la meilleure diversification. "
            "Action prioritaire: formule la decision a prendre en une phrase, puis on la transforme en prochaine etape executable."
        ),
    }

    return {
        "analysis": responses.get(focus, responses["general"]),
        "context_score": score,
        "tier": tier,
        "focus": focus,
        "autopilot": None,
    }


def get_advisor_free(user_email, message):
    return advisor_logic(user_email, message)


def get_advisor_premium(user_email, message):
    return advisor_logic(user_email, message)


def get_advisor_elite(user_email, message):
    return advisor_logic(user_email, message)


def portfolio_manager(user_email, message):
    return advisor_logic(user_email, f"Analyse portefeuille: {message}")


def portfolio_autopilot(user_email, message):
    user_id = None

    with engine.connect() as conn:
        user_id = get_user_id(conn, user_email)

    return run_autopilot_safely(
        user_email=user_email,
        portfolio=compact_portfolio(get_user_portfolio(user_id) if user_id else {}),
        market={},
        context={},
        llm_text=message[:900],
        level="free",
    )
