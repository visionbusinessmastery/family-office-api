from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


# =========================
# SAFE KEY FUNCTION
# =========================
def safe_user_key(request: Request):
    """
    Priorité:
    1. user_email si dispo
    2. IP fallback
    """

    try:
        user = getattr(request.state, "user_email", None)
        if user:
            return user
    except Exception:
        pass

    return get_remote_address(request)


# =========================
# LIMITER GLOBAL
# =========================
limiter = Limiter(
    key_func=safe_user_key,
    default_limits=["100/minute"]
)
