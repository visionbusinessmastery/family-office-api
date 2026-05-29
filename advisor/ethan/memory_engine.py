import json

from sqlalchemy import text

from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION
from advisor.ethan.strategy_engine import safe_int


def _versioned_context_profile(profile):
    profile = profile if isinstance(profile, dict) else {}
    if profile.get("cache_version") == ETHAN_GLOBAL_CACHE_VERSION:
        return profile

    preserved_keys = [
        "priority_goal",
        "goals",
        "time_constraint",
        "family_constraint",
        "has_children",
        "expertise",
        "professional_context",
        "business_context",
        "businesses",
    ]
    return {
        key: profile[key]
        for key in preserved_keys
        if profile.get(key)
    }


def get_memory(conn, user_id):
    if not user_id:
        return {}

    row = conn.execute(text("""
        SELECT strategic_summary, session_summary, last_topic, context_profile, key_signals
        FROM ethan_memory
        WHERE user_id = :user_id
    """), {"user_id": user_id}).fetchone()

    if not row:
        return {}

    return {
        "strategic_summary": row.strategic_summary,
        "session_summary": row.session_summary,
        "last_topic": row.last_topic,
        "context_profile": _versioned_context_profile(row.context_profile or {}),
        "key_signals": row.key_signals,
    }


def build_life_context(conn, user_id, memory=None):
    memory = memory or {}
    profile = {}
    try:
        row = conn.execute(text("""
            SELECT first_name, goals, horizon, investor_profile, risk_level,
                   motivation, has_children, transmission_goal, governance_need,
                   family_strategy
            FROM user_wealth_profiles
            WHERE user_id = :user_id
        """), {"user_id": user_id}).fetchone()
        if row:
            profile = {
                "first_name": row.first_name,
                "goals": [item for item in (row.goals or "").split("|") if item],
                "horizon": row.horizon,
                "professional_context": row.investor_profile,
                "risk_level": row.risk_level,
                "motivation": row.motivation,
                "has_children": bool(row.has_children),
                "transmission_goal": row.transmission_goal,
                "governance_need": row.governance_need,
                "family_strategy": row.family_strategy,
            }
    except Exception:
        profile = {}

    try:
        ventures = conn.execute(text("""
            SELECT asset_type, name, revenue, charges
            FROM venture_assets
            WHERE user_id = :user_id
            ORDER BY updated_at DESC, id DESC
            LIMIT 3
        """), {"user_id": user_id}).fetchall()
        profile["businesses"] = [
            {
                "type": row.asset_type,
                "name": row.name,
                "revenue": float(row.revenue or 0),
                "charges": float(row.charges or 0),
            }
            for row in ventures
        ]
    except Exception:
        profile["businesses"] = []

    remembered = memory.get("context_profile") if isinstance(memory, dict) else {}
    if isinstance(remembered, dict):
        for key, value in remembered.items():
            if value and not profile.get(key):
                profile[key] = value

    return profile


def extract_context_signals(message):
    normalized = (message or "").lower()
    signals = {}

    if any(word in normalized for word in ["peu de temps", "pas le temps", "temps limite", "fatigue", "charge mentale"]):
        signals["time_constraint"] = "temps limite / charge mentale a respecter"
    if any(word in normalized for word in ["enfant", "enfants", "famille", "heritiers"]):
        signals["family_constraint"] = "responsabilites familiales"
    if any(word in normalized for word in ["marketing", "communication", "agence", "ads", "contenu"]):
        signals["expertise"] = "marketing / acquisition / communication"
    if any(word in normalized for word in ["salarie", "cdi", "emploi"]):
        signals["professional_context"] = "salarie"
    if any(word in normalized for word in ["entreprise", "business", "activite", "freelance"]):
        signals["business_context"] = "activite business existante ou a developper"
    if any(word in normalized for word in ["augmenter mes revenus", "plus de revenus", "revenus complementaires", "gagner plus"]):
        signals["priority_goal"] = "augmenter les revenus"

    return signals


def summarize_context_profile(profile):
    fragments = []
    if profile.get("priority_goal"):
        fragments.append(f"objectif prioritaire: {profile['priority_goal']}")
    goals = profile.get("goals") or []
    if goals:
        fragments.append(f"objectifs: {', '.join(goals[:3])}")
    if profile.get("time_constraint"):
        fragments.append(profile["time_constraint"])
    if profile.get("has_children") or profile.get("family_constraint"):
        fragments.append("contexte familial a prendre en compte")
    if profile.get("expertise"):
        fragments.append(f"expertise: {profile['expertise']}")
    if profile.get("professional_context"):
        fragments.append(f"situation: {profile['professional_context']}")
    if profile.get("business_context"):
        fragments.append(profile["business_context"])
    businesses = profile.get("businesses") or []
    if businesses:
        fragments.append("business suivi: " + ", ".join(item.get("name") or item.get("type") for item in businesses[:2]))
    return " | ".join(fragment for fragment in fragments if fragment)


def update_memory(
    conn,
    user_id,
    message,
    answer,
    context,
    memory=None,
    response_strategy=None,
    classify_task_fn=None,
    classify_request_fn=None,
):
    if not user_id:
        return

    classify_request_fn = classify_request_fn or (lambda _message: "medium")
    classify_task_fn = classify_task_fn or (lambda _message, _complexity: "conversation")

    topic = classify_task_fn(message, classify_request_fn(message))
    answer_excerpt = (answer or "")[:500]
    existing_profile = {}
    if isinstance(memory, dict) and isinstance(memory.get("context_profile"), dict):
        existing_profile = dict(memory.get("context_profile") or {})
    next_profile = {**existing_profile, **extract_context_signals(message)}
    next_profile["cache_version"] = ETHAN_GLOBAL_CACHE_VERSION
    if response_strategy:
        next_profile["_last_primary_intent"] = response_strategy.get("primary_intent")
        next_profile["_last_strategic_angle"] = response_strategy.get("strategic_angle")
        next_profile["_last_output_style"] = response_strategy.get("output_style")
        next_profile["last_angle_used"] = response_strategy.get("strategic_angle")
        next_profile["last_style_used"] = response_strategy.get("output_style")
        next_profile["last_output_type"] = response_strategy.get("output_type") or response_strategy.get("output_style")
        next_profile["last_cognitive_lens"] = response_strategy.get("cognitive_lens")
        next_profile["response_diversity_counter"] = safe_int(next_profile.get("response_diversity_counter"), 0) + 1
    key_signals = summarize_context_profile(next_profile) or summarize_context_profile(context.get("life_context") or {})
    session_summary = (
        f"Derniere question: {message[:220]} | "
        f"Orientation Ethan: {answer_excerpt}"
    )
    strategic_summary = (
        key_signals or
        f"Plan {context.get('plan', 'FREE')}. Niveau {context.get('level', 'non precise')}."
    )

    conn.execute(text("""
        INSERT INTO ethan_memory (
            user_id, strategic_summary, session_summary, last_topic,
            context_profile, key_signals, updated_at
        )
        VALUES (
            :user_id, :strategic_summary, :session_summary, :last_topic,
            CAST(:context_profile AS JSONB), :key_signals, NOW()
        )
        ON CONFLICT (user_id)
        DO UPDATE SET
            strategic_summary = EXCLUDED.strategic_summary,
            session_summary = EXCLUDED.session_summary,
            last_topic = EXCLUDED.last_topic,
            context_profile = EXCLUDED.context_profile,
            key_signals = EXCLUDED.key_signals,
            updated_at = NOW()
    """), {
        "user_id": user_id,
        "strategic_summary": strategic_summary,
        "session_summary": session_summary,
        "last_topic": topic,
        "context_profile": json.dumps(next_profile),
        "key_signals": key_signals,
    })
