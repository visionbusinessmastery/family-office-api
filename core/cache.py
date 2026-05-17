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
