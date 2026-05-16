import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

redis_client = None

if REDIS_URL:
    try:
        redis_client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            ssl_cert_reqs=None
        )
    except Exception as e:
        print("🔴 Redis init failed:", str(e))
        redis_client = None


def test_redis():
    if not redis_client:
        return False
    try:
        return redis_client.ping()
    except:
        return False
