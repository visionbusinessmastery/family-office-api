import redis
import os
import logging

REDIS_URL = os.getenv("REDIS_URL")
logger = logging.getLogger(__name__)

redis_client = None

try:
    if REDIS_URL:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            ssl_cert_reqs=None  # 🔥 IMPORTANT FIX SSL CLOUD
        )
except Exception as e:
    logger.warning("Redis init error: %s", e)
    redis_client = None


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
