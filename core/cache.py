import logging
import os
import time

import redis


REDIS_URL = os.getenv("REDIS_URL")
REDIS_DISABLE_SSL = os.getenv("REDIS_DISABLE_SSL", "").lower() in {
    "1",
    "true",
    "yes",
}
REDIS_TIMEOUT_SECONDS = float(os.getenv("REDIS_TIMEOUT_SECONDS", "1.5"))
REDIS_DISABLE_COOLDOWN_SECONDS = int(
    os.getenv("REDIS_DISABLE_COOLDOWN_SECONDS", "300")
)

logger = logging.getLogger(__name__)


class SafeRedisClient:
    def __init__(self, client):
        self._client = client
        self._disabled_until = 0.0
        self._last_log_at = 0.0

    def __bool__(self):
        return self._client is not None and time.time() >= self._disabled_until

    def _log_once(self, action: str, error: Exception):
        now = time.time()
        if now - self._last_log_at >= 60:
            logger.warning("Redis %s disabled temporarily: %s", action, error)
            self._last_log_at = now

    def _call(self, action: str, *args, **kwargs):
        if not self:
            return None

        try:
            return getattr(self._client, action)(*args, **kwargs)
        except Exception as exc:
            self._disabled_until = time.time() + REDIS_DISABLE_COOLDOWN_SECONDS
            self._log_once(action, exc)
            return None

    def get(self, *args, **kwargs):
        return self._call("get", *args, **kwargs)

    def setex(self, *args, **kwargs):
        return self._call("setex", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._call("delete", *args, **kwargs)

    def scan_iter(self, *args, **kwargs):
        result = self._call("scan_iter", *args, **kwargs)
        return result or []


def _redis_options(url: str):
    options = {
        "decode_responses": True,
        "socket_connect_timeout": REDIS_TIMEOUT_SECONDS,
        "socket_timeout": REDIS_TIMEOUT_SECONDS,
        "retry_on_timeout": False,
    }

    if url.startswith("rediss://"):
        options["ssl_cert_reqs"] = None

    return options


def _make_client(url: str):
    client = redis.from_url(url, **_redis_options(url))
    client.ping()
    return client


def _resolve_redis_client():
    if not REDIS_URL:
        return None

    url = REDIS_URL
    if REDIS_DISABLE_SSL and url.startswith("rediss://"):
        url = "redis://" + url[len("rediss://") :]

    try:
        return SafeRedisClient(_make_client(url))
    except Exception as exc:
        if "WRONG_VERSION_NUMBER" in str(exc) and url.startswith("rediss://"):
            fallback_url = "redis://" + url[len("rediss://") :]
            try:
                logger.warning(
                    "Redis SSL handshake failed; retrying without SSL for this connection."
                )
                return SafeRedisClient(_make_client(fallback_url))
            except Exception as fallback_exc:
                logger.warning("Redis fallback init error: %s", fallback_exc)
                return None

        logger.warning("Redis init error: %s", exc)
        return None


redis_client = _resolve_redis_client()


def delete_cache_keys(*keys: str):
    try:
        if redis_client and keys:
            redis_client.delete(*[key for key in keys if key])
    except Exception:
        pass


def delete_cache_patterns(*patterns: str):
    try:
        if not redis_client:
            return

        keys = []
        for pattern in patterns:
            keys.extend(list(redis_client.scan_iter(pattern)))

        if keys:
            redis_client.delete(*keys)
    except Exception:
        pass
