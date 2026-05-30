import json
import logging
import unicodedata

from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION


logger = logging.getLogger(__name__)
ETHAN_CORE_SYSTEM = "ETHAN_CORE_V4"
CORE_EMPTY_STATUS = "empty"
SAFE_MODEL_FALLBACKS = ["gpt-4o-mini", "gpt-4.1-mini"]

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


def _extract_text_part(part):
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        return part.get("text") or part.get("content") or ""
    return getattr(part, "text", None) or getattr(part, "content", None) or ""


def extract_llm_text(response):
    try:
        message = response.choices[0].message
    except Exception:
        return ""

    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(text).strip()
            for text in (_extract_text_part(part) for part in content)
            if str(text or "").strip()
        ).strip()

    return str(content or "").strip()


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

    selected_model = model
    attempted = set()
    attempts = []
    last_empty = None

    for candidate in [model, fallback_model, *SAFE_MODEL_FALLBACKS]:
        if not candidate or candidate in attempted:
            continue
        attempted.add(candidate)
        attempts.append((candidate, "max_completion_tokens"))
        attempts.append((candidate, "max_tokens"))

    for candidate, token_param in attempts:
        try:
            response = _call(candidate, token_param)
            selected_model = candidate
            llm_text = extract_llm_text(response)
            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", None) or estimate_tokens_fn(json.dumps(messages))
            output_tokens = getattr(usage, "completion_tokens", None) or estimate_tokens_fn(llm_text)

            if not llm_text:
                last_empty = (input_tokens, output_tokens, selected_model)
                logger.warning(
                    "Ethan OpenAI returned empty content; trying next model",
                    extra={"model": candidate, "token_param": token_param},
                )
                continue

            if not is_legacy_ethan_response(llm_text):
                set_cache_fn(llm_cache_key, llm_text, ttl=1800)
            return llm_text, False, input_tokens, output_tokens, selected_model, "ready"
        except Exception:
            logger.warning(
                "Ethan OpenAI attempt failed",
                extra={"model": candidate, "token_param": token_param},
                exc_info=True,
            )

    if last_empty:
        input_tokens, output_tokens, selected_model = last_empty
        return None, False, input_tokens, output_tokens, selected_model, "openai_empty_output"

    return None, False, estimate_tokens_fn(json.dumps(messages)), 0, selected_model, "openai_call_failed"


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
