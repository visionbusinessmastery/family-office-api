import hashlib
import json
import os
from datetime import date

from sqlalchemy import text

from advisor.autopilot_v4_engine import get_autopilot_v4
from advisor.ethan.context_engine import compact_context, compact_portfolio
from advisor.ethan.memory_engine import build_life_context, get_memory, update_memory
from advisor.ethan.openai_gateway import ethan_chat_completion, is_ethan_openai_configured
from advisor.ethan.prompt_engine import build_advisor_messages
from advisor.ethan.strategy_engine import build_response_strategy
from auth.utils import get_user_id
from core.cache import redis_client
from database import engine
from portfolio.service import get_user_portfolio
from product.entitlements import normalize_plan, plan_allows, resolve_effective_plan
from advisor.user_state import centralized_user_state_builder


_ethan_schema_ready = False
ADVISOR_CACHE_VERSION = "v13-stale-response-guard"

LEGACY_ETHAN_RESPONSE_PATTERNS = [
    "ton score est",
    "ton score ",
    "score 39/100",
    "pour le cashflow",
    "action simple",
    "action prioritaire",
    "priorite:",
    "priorité:",
    "clarifier la capacite",
    "capacite mensuelle disponible",
    "capacité mensuelle disponible",
]

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
            context_profile JSONB,
            key_signals TEXT,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))
    conn.execute(text("ALTER TABLE ethan_memory ADD COLUMN IF NOT EXISTS context_profile JSONB"))
    conn.execute(text("ALTER TABLE ethan_memory ADD COLUMN IF NOT EXISTS key_signals TEXT"))

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


def _normalize_legacy_text(value) -> str:
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False, default=str)
    else:
        raw = str(value or "")

    return (
        raw.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("â", "a")
        .replace("î", "i")
        .replace("ô", "o")
        .replace("û", "u")
    )


def is_legacy_ethan_response(value) -> bool:
    normalized = _normalize_legacy_text(value)
    return any(
        _normalize_legacy_text(pattern) in normalized
        for pattern in LEGACY_ETHAN_RESPONSE_PATTERNS
    )


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


def get_llm_response(messages, model, max_output_tokens):
    prompt_hash = stable_hash({"messages": messages, "model": model, "max": max_output_tokens})
    llm_cache_key = f"llm:{prompt_hash}"

    cached = get_cache(llm_cache_key)
    if cached and not is_legacy_ethan_response(cached):
        return cached, True, estimate_tokens(json.dumps(messages)), estimate_tokens(cached), model

    if not is_ethan_openai_configured():
        return None, False, estimate_tokens(json.dumps(messages)), 0, model

    def _call(selected_model, token_param="max_completion_tokens"):
        kwargs = {
            "model": selected_model,
            "messages": messages,
            token_param: max_output_tokens,
        }
        return ethan_chat_completion(**kwargs)

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
        if not is_legacy_ethan_response(llm_text):
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


def advisor_logic(user_email, message, level=None, bypass_cache=False):
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
        life_context = build_life_context(conn, user_id, memory)
        context["life_context"] = life_context
        response_strategy = build_response_strategy(message, memory)

        fingerprint = stable_hash({
            "version": ADVISOR_CACHE_VERSION,
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
            "response_strategy": response_strategy,
        })[:16]
        cache_key = f"advisor:{build_hash(user_email, message, plan, complexity, fingerprint)}"

        cached = None if bypass_cache else get_cache(cache_key)
        if cached and not is_legacy_ethan_response(cached):
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
            response_strategy=response_strategy,
        )

        llm_text, llm_cache_hit, input_tokens, output_tokens, actual_model = get_llm_response(
            messages,
            model,
            config["max_output_tokens"],
        )

        if not llm_text or is_legacy_ethan_response(llm_text):
            result = build_fallback_response(
                context,
                opportunities,
                tier,
                message=message,
                portfolio=portfolio,
                response_strategy=response_strategy,
            )
            update_memory(
                conn,
                user_id,
                message,
                result.get("analysis"),
                context,
                memory,
                response_strategy,
                classify_task_fn=classify_task,
                classify_request_fn=classify_request,
            )
            record_usage(conn, user_id, user_email, plan, tier, task_type, complexity, actual_model, False, input_tokens, 0)
            if not bypass_cache:
                set_cache(cache_key, result, ttl=180)
            return result

        update_memory(
            conn,
            user_id,
            message,
            llm_text,
            context,
            memory,
            response_strategy,
            classify_task_fn=classify_task,
            classify_request_fn=classify_request,
        )
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
            "autopilot": None,
        }

        if not bypass_cache:
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


def _fallback_focus(message: str) -> str:
    normalized = (message or "").lower()
    if any(word in normalized for word in ["immobilier", "residence", "locatif", "loyer", "travaux"]):
        return "real_estate"
    if any(word in normalized for word in ["opportunite", "opportunites", "deal", "signal", "source"]):
        return "opportunities"
    if any(word in normalized for word in [
        "business",
        "entreprise",
        "startup",
        "franchise",
        "reprise",
        "marketing",
        "communication",
        "commerce",
        "client",
        "offre",
        "vente",
        "revenu",
        "revenus",
    ]):
        return "business"
    if any(word in normalized for word in ["cashflow", "charge", "charges", "epargne", "budget", "liquidite", "tresorerie"]):
        return "cashflow"
    if any(word in normalized for word in ["risque", "concentration", "exposition", "diversification"]):
        return "risk"
    if any(word in normalized for word in ["portfolio", "portefeuille", "action", "etf", "crypto", "forex"]):
        return "portfolio"
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


def _allows_premium_depth(tier: str) -> bool:
    return tier not in ["ESSENTIALS", "FREE", "BASIC", None]


def build_fallback_response(
    context,
    opportunities,
    tier="ESSENTIALS",
    message=None,
    portfolio=None,
    response_strategy=None,
):
    score = get_context_score(context)
    opportunity_count = _opportunity_count(opportunities)
    focus = _fallback_focus(message or "")
    top_exposure = _top_portfolio_exposure(portfolio or {})
    life_context = context.get("life_context") or {}
    has_family_load = bool(life_context.get("has_children") or life_context.get("family_constraint"))
    time_constraint = life_context.get("time_constraint")
    expertise = life_context.get("expertise")
    goal = life_context.get("priority_goal") or life_context.get("motivation")
    business_hint = life_context.get("business_context") or (
        "business existant" if life_context.get("businesses") else None
    )
    response_strategy = response_strategy or build_response_strategy(message or "", {})
    output_style = response_strategy.get("output_style") or "quiet_analyst"
    cognitive_lens = response_strategy.get("cognitive_lens") or "human_context"

    context_intro = "Dans ta situation"
    if has_family_load and time_constraint:
        context_intro = "Avec une charge familiale et peu de temps"
    elif time_constraint:
        context_intro = "Avec peu de temps disponible"
    elif expertise:
        context_intro = f"En partant de ton expertise {expertise}"

    revenue_lever = (
        f"{context_intro}, le levier le plus realiste est de monetiser une competence deja presente"
        if expertise
        else f"{context_intro}, le levier le plus realiste est de choisir une action qui n'ajoute pas trop de complexite"
    )
    if goal and "revenu" in str(goal).lower():
        revenue_lever += " pour augmenter les revenus sans disperser ton energie"
    if business_hint:
        revenue_lever += " et de l'adosser a ton activite existante"

    responses = {
        "real_estate": (
            "Le point delicat avec l'immobilier, ce n'est pas seulement le prix d'achat. C'est surtout la charge que l'actif impose ensuite. "
            "Je regarderais un seul bien comparable, en incluant charges, vacance et travaux, avant d'aller plus loin."
        ),
        "opportunities": (
            f"Il y a {opportunity_count} piste(s) visibles, mais le vrai gain vient du tri, pas du volume. "
            "Garde seulement celle qui ameliore une faiblesse claire sans ajouter de complexite inutile."
        ),
        "cashflow": (
            "Le sujet n'est pas d'analyser davantage, mais de choisir le levier de revenu le moins lourd a executer. "
            f"{revenue_lever}. "
            "Tu peux tester une action revenue courte, mesurable, et compatible avec ton quotidien."
        ),
        "risk": (
            "Une opportunite attractive peut devenir fragile si elle renforce deja ta poche dominante. "
            f"Le point de risque principal semble etre la concentration: ta poche dominante est {top_exposure}. "
            "Avant d'ajouter une ligne, garde une limite claire sur ce que cette poche peut representer."
        ),
        "portfolio": (
            "Le portefeuille doit raconter une these, pas seulement additionner des actifs. "
            f"Pour le portefeuille, je regarderais d'abord l'allocation plutot que le prochain actif. Ta poche la plus visible est {top_exposure}. "
            "La prochaine position devrait avoir un role net: stabiliser, diversifier, produire du revenu ou chercher de la valorisation."
        ),
        "business": (
            "Si une expertise existe deja, le meilleur levier est souvent une offre plus nette, pas un nouveau projet. "
            f"{revenue_lever}. "
            "Je testerais une promesse courte orientee PME ou independants: un audit marketing express, limite dans le temps, qui peut se vendre sans alourdir tes soirees."
        ),
        "legacy": (
            "En Legacy, la vraie performance est la continuite, pas seulement la croissance. "
            "Pour la partie Legacy, l'objectif n'est pas d'aller vite mais de rendre le patrimoine plus transmissible et moins dependant de toi. "
            "Le mouvement utile serait de rendre visibles les beneficiaires, documents essentiels et roles familiaux."
        ),
        "progression": (
            "La prochaine progression doit etre verifiable par le backend, sinon elle reste une intention. "
            "Pour progresser, l'action la plus rentable est souvent la donnee manquante la plus simple. "
            "Choisis une mission concrete et mesurable aujourd'hui plutot qu'une grande refonte."
        ),
        "general": (
            "La bonne decision est celle qui respecte ton contexte reel avant d'optimiser le patrimoine. "
            f"{revenue_lever}. Je vois {opportunity_count} opportunite(s), mais je ne les mettrais pas toutes au meme niveau. "
            "Le plus propre serait de choisir une seule avancee compatible avec ton temps reel cette semaine."
        ),
    }
    analysis = responses.get(focus, responses["general"])
    if _allows_premium_depth(tier) and cognitive_lens == "question":
        analysis = "La vraie question ici est de savoir quelle decision allege la suite au lieu de l'alourdir. " + analysis
    elif _allows_premium_depth(tier) and cognitive_lens == "insight":
        analysis = "Le signal interessant, c'est que la meilleure avancee n'est pas forcement la plus spectaculaire. " + analysis
    elif _allows_premium_depth(tier) and cognitive_lens == "human_context":
        analysis = analysis.replace("La bonne decision", "La bonne decision, dans ton rythme reel,")
    if _allows_premium_depth(tier) and output_style == "human_coach":
        analysis = analysis.replace("Je regarderais", "Tu peux regarder")
    elif _allows_premium_depth(tier) and output_style == "risk_lens" and focus not in ["risk", "real_estate"]:
        analysis += " Ce qui merite attention, c'est de ne pas ajouter une decision qui augmente ta charge mentale."
    elif _allows_premium_depth(tier) and output_style == "action_trigger":
        natural_triggers = {
            "real_estate": "Prends un seul dossier comparable et regarde-le avec charges, vacance et travaux avant d'en ouvrir un deuxieme.",
            "opportunities": "Mets les pistes secondaires en attente et avance seulement sur celle qui peut etre testee cette semaine.",
            "cashflow": "Teste une petite action de revenu que tu peux executer sans changer ton rythme quotidien.",
            "risk": "Fixe une limite d'exposition avant toute nouvelle position.",
            "portfolio": "Donne un role clair a la prochaine ligne avant de l'ajouter.",
            "business": "Formule l'offre en une phrase et teste-la avant de construire plus lourd.",
            "legacy": "Rends visibles les beneficiaires et les documents essentiels avant d'ajouter de nouvelles optimisations.",
            "progression": "Choisis une mission mesurable que le backend pourra verifier, puis laisse le reste pour plus tard.",
            "general": "Garde une seule avancee concrete pour cette semaine, compatible avec ton temps reel.",
        }
        analysis += " " + natural_triggers.get(focus, natural_triggers["general"])

    return {
        "analysis": analysis,
        "context_score": score,
        "tier": tier,
        "focus": focus,
        "autopilot": None,
    }


def get_advisor_free(user_email, message, bypass_cache=False):
    return advisor_logic(user_email, message, bypass_cache=bypass_cache)


def get_advisor_premium(user_email, message, bypass_cache=False):
    return advisor_logic(user_email, message, bypass_cache=bypass_cache)


def get_advisor_elite(user_email, message, bypass_cache=False):
    return advisor_logic(user_email, message, bypass_cache=bypass_cache)


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
        llm_text=None,
        level="free",
    )
