from fastapi import HTTPException

from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION
from advisor.ethan.output_renderer import ETHAN_TEXT_ORIGIN


ALLOWED_FRONTEND_KEYS = {"analysis", "metadata"}
FORBIDDEN_METADATA_KEYS = {
    "input",
    "message",
    "prompt",
    "raw",
    "raw_signal",
    "raw_llm_output",
    "user_text",
    "llm_text",
}


def _contract_error(reason):
    raise HTTPException(
        status_code=500,
        detail={
            "error": "ethan_contract_violation",
            "reason": reason,
            "cache_version": ETHAN_GLOBAL_CACHE_VERSION,
        },
    )


def _contains_forbidden_key(value):
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) in FORBIDDEN_METADATA_KEYS:
                return True
            if _contains_forbidden_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def validate_ethan_frontend_contract(payload):
    if not isinstance(payload, dict):
        _contract_error("payload_must_be_object")

    extra_keys = set(payload.keys()) - ALLOWED_FRONTEND_KEYS
    if extra_keys:
        _contract_error(f"unexpected_top_level_keys:{sorted(extra_keys)}")

    analysis = payload.get("analysis")
    metadata = payload.get("metadata")

    if not isinstance(analysis, str):
        _contract_error("analysis_must_be_string")

    if not isinstance(metadata, dict):
        _contract_error("metadata_must_be_object")

    if metadata.get("text_origin") != ETHAN_TEXT_ORIGIN:
        _contract_error("analysis_text_origin_must_be_output_renderer")

    if metadata.get("cache_version") != ETHAN_GLOBAL_CACHE_VERSION:
        _contract_error("cache_version_mismatch")

    if _contains_forbidden_key(metadata):
        _contract_error("metadata_contains_forbidden_text_source")

    return {
        "analysis": analysis,
        "metadata": metadata,
    }
