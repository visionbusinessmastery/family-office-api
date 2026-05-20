import os


SENSITIVE_KEYS = {"authorization", "cookie", "password", "token", "secret", "api_key"}


def _scrub(value):
    if isinstance(value, dict):
        return {
            key: "[Filtered]" if key.lower() in SENSITIVE_KEYS else _scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def before_send(event, hint):
    return _scrub(event)


def init_sentry(app=None):
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", os.getenv("STRIPE_MODE", "sandbox")),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0")),
            before_send=before_send,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            send_default_pii=False,
        )
        return True
    except Exception:
        return False


def capture_exception(exc, context=None):
    try:
        import sentry_sdk

        if context:
            with sentry_sdk.configure_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass
