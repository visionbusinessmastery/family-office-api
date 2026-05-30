import json
import unicodedata

from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION


ETHAN_CORE_SYSTEM = "ETHAN_CORE_V4"
CORE_EMPTY_STATUS = "empty"

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


def with_core_contract(result, mode: str):
    if not isinstance(result, dict):
        result = {"status": CORE_EMPTY_STATUS}

    next_result = dict(result)
    analysis = str(next_result.get("analysis") or "").strip()
    next_result["analysis"] = analysis
    next_result["source"] = "ethan_core"
    next_result["mode"] = mode
    next_result["system"] = ETHAN_CORE_SYSTEM
    return next_result


def normalize_legacy_text(value) -> str:
    if isinstance(value, (dict, list)):
        raw = json.dumps(value, ensure_ascii=False, default=str)
    else:
        raw = str(value or "")

    normalized = unicodedata.normalize("NFD", raw.lower())
    normalized = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )

    return (
        normalized
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
    normalized = normalize_legacy_text(value)
    return any(
        normalize_legacy_text(pattern) in normalized
        for pattern in LEGACY_ETHAN_RESPONSE_PATTERNS
    )


def get_context_score(context):
    score = context.get("global_score") or context.get("score", 0)

    if isinstance(score, dict):
        return score.get("score", 0)

    return score


def build_llm_response_data(raw_llm_output, context, tier="ESSENTIALS", *, complexity=None, soft_budget_active=False, cache_hit=False):
    return {
        "status": "ready" if raw_llm_output else CORE_EMPTY_STATUS,
        "raw_llm_output": raw_llm_output or "",
        "context_score": get_context_score(context or {}),
        "tier": tier,
        "complexity": complexity,
        "soft_budget_active": soft_budget_active,
        "cache_hit": cache_hit,
        "autopilot": None,
    }


def get_llm_response(
    messages,
    model,
    max_output_tokens,
    *,
    stable_hash_fn,
    get_cache_fn,
    set_cache_fn,
    estimate_tokens_fn,
    is_model_configured_fn,
    chat_completion_fn,
    fallback_model,
):
    import json

    prompt_hash = stable_hash_fn({
        "version": ETHAN_GLOBAL_CACHE_VERSION,
        "messages": messages,
        "model": model,
        "max": max_output_tokens,
    })
    llm_cache_key = f"llm:{prompt_hash}"

    cached = get_cache_fn(llm_cache_key)
    if cached and not is_legacy_ethan_response(cached):
        return cached, True, estimate_tokens_fn(json.dumps(messages)), estimate_tokens_fn(cached), model, "cache_hit"

    if not is_model_configured_fn():
        return None, False, estimate_tokens_fn(json.dumps(messages)), 0, model, "openai_unconfigured"

    def _call(selected_model, token_param="max_completion_tokens"):
        kwargs = {
            "model": selected_model,
            "messages": messages,
            token_param: max_output_tokens,
        }
        return chat_completion_fn(**kwargs)

    response = None

    try:
        response = _call(model)
    except Exception:
        try:
            response = _call(fallback_model)
            model = fallback_model
        except Exception:
            try:
                response = _call(fallback_model, "max_tokens")
                model = fallback_model
            except Exception:
                return None, False, estimate_tokens_fn(json.dumps(messages)), 0, model, "openai_call_failed"

    try:
        llm_text = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", None) or estimate_tokens_fn(json.dumps(messages))
        output_tokens = getattr(usage, "completion_tokens", None) or estimate_tokens_fn(llm_text)
        if not is_legacy_ethan_response(llm_text):
            set_cache_fn(llm_cache_key, llm_text, ttl=1800)
        return llm_text, False, input_tokens, output_tokens, model, "ready"
    except Exception:
        return None, False, estimate_tokens_fn(json.dumps(messages)), 0, model, "openai_parse_failed"


def build_fallback_response(
    context,
    opportunities,
    tier="ESSENTIALS",
    message=None,
    portfolio=None,
    response_strategy=None,
    compact_portfolio_fn=None,
    build_response_strategy_fn=None,
):
    return {"status": CORE_EMPTY_STATUS}
