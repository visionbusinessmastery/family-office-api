import redis
import os

REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

try:
    if REDIS_URL:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            ssl_cert_reqs=None  # 🔥 IMPORTANT FIX SSL CLOUD
        )
except Exception as e:
    print("[REDIS INIT ERROR]", e)
    redis_client = None
