import os
import redis

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    raise Exception("REDIS_URL manquante")

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
    ssl_cert_reqs=None  # important pour Redis Cloud
)

# TEST SAFE (optionnel)
try:
    redis_client.ping()
    print("🟢 REDIS CONNECTÉ OK")
except Exception as e:
    print("🔴 REDIS ERROR:", str(e))
