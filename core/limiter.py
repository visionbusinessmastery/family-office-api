from slowapi import Limiter
from auth.utils import get_user_key

limiter = Limiter(
    key_func=get_user_key,
    default_limits=["100/minute"]  # 🔥 fallback global
)
