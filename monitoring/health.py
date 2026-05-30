import os
import time

from sqlalchemy import text

from advisor.ethan.openai_gateway import ethan_chat_completion
from core.cache import redis_client
from database import engine
from billing.routes import PLANS


def _timed(check):
    started = time.perf_counter()
    try:
        result = check()
        status = result.get("status", "ok") if isinstance(result, dict) else "ok"
        payload = result if isinstance(result, dict) else {}
    except Exception as exc:
        status = "down"
        payload = {"error": exc.__class__.__name__}
    payload["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    payload["status"] = status
    return payload


def check_db():
    def run():
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return _timed(run)


def check_cache():
    def run():
        if not redis_client:
            return {"status": "degraded", "detail": "Redis not configured"}
        redis_client.ping()
        return {"status": "ok"}

    return _timed(run)


def _openai_model_candidates():
    candidates = [
        os.getenv("ETHAN_MODEL_STANDARD", "gpt-5-mini"),
        os.getenv("ETHAN_MODEL_FALLBACK"),
        os.getenv("OPENAI_MODEL"),
        "gpt-4o-mini",
        "gpt-4.1-mini",
    ]
    seen = set()
    return [model for model in candidates if model and not (model in seen or seen.add(model))]


def _check_openai_live():
    if not os.getenv("OPENAI_API_KEY"):
        return {
            "live_status": "skipped",
            "live_error": "openai_unconfigured",
        }

    for model in _openai_model_candidates():
        for token_param in ["max_completion_tokens", "max_tokens"]:
            try:
                response = ethan_chat_completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": "Healthcheck White Rock. Reponds OK."},
                        {"role": "user", "content": "ping"},
                    ],
                    **{token_param: 8},
                )
                text = str(response.choices[0].message.content or "").strip()
                if text:
                    return {
                        "live_status": "ok",
                        "tested_model": model,
                        "token_param": token_param,
                        "has_text": True,
                    }
                last_error = {
                    "live_status": "empty_output",
                    "tested_model": model,
                    "token_param": token_param,
                    "has_text": False,
                }
            except Exception as exc:
                last_error = {
                    "live_status": "failed",
                    "tested_model": model,
                    "token_param": token_param,
                    "error_type": exc.__class__.__name__,
                }

    return last_error


def check_openai(live: bool = False):
    configured = bool(os.getenv("OPENAI_API_KEY"))
    payload = {
        "status": "ok" if configured else "degraded",
        "configured": configured,
        "models": {
            "light": os.getenv("ETHAN_MODEL_LIGHT", "gpt-5-nano"),
            "standard": os.getenv("ETHAN_MODEL_STANDARD", "gpt-5-mini"),
            "premium": os.getenv("ETHAN_MODEL_PREMIUM", "gpt-5"),
            "dynasty": os.getenv("ETHAN_MODEL_DYNASTY", os.getenv("ETHAN_MODEL_PREMIUM", "gpt-5")),
        },
    }

    if live:
        live_payload = _check_openai_live()
        payload.update(live_payload)
        if live_payload.get("live_status") not in ["ok"]:
            payload["status"] = "degraded"

    return payload


def check_stripe():
    missing_prices = [
        plan["price_env"]
        for plan_id, plan in PLANS.items()
        if plan_id != "free" and plan.get("price_env") and not os.getenv(plan["price_env"])
    ]
    configured = bool(os.getenv("STRIPE_SECRET_KEY"))
    webhook = bool(os.getenv("STRIPE_WEBHOOK_SECRET"))
    status = "ok" if configured and webhook and not missing_prices else "degraded"
    return {
        "status": status,
        "configured": configured,
        "webhook_configured": webhook,
        "mode": os.getenv("STRIPE_MODE", "sandbox"),
        "missing_prices": missing_prices,
    }


def check_sentry():
    return {
        "status": "ok" if bool(os.getenv("SENTRY_DSN")) else "degraded",
        "configured": bool(os.getenv("SENTRY_DSN")),
    }


def check_posthog():
    return {
        "status": "ok" if bool(os.getenv("POSTHOG_API_KEY")) else "degraded",
        "configured": bool(os.getenv("POSTHOG_API_KEY")),
        "host": os.getenv("POSTHOG_HOST", "https://app.posthog.com"),
    }


def system_health():
    checks = {
        "db": check_db(),
        "cache": check_cache(),
        "openai": check_openai(),
        "stripe": check_stripe(),
        "sentry": check_sentry(),
        "posthog": check_posthog(),
    }
    status = "ok" if all(item["status"] == "ok" for item in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
