import logging
from uuid import uuid4

from fastapi import HTTPException


logger = logging.getLogger(__name__)


# =========================
# SAFE EXECUTOR (PRODUCTION SAFE)
# =========================
def safe_execute(func, data=None, module_name=""):
    try:
        return func(data) if data else func()

    except HTTPException as e:
        # 👉 Laisse FastAPI gérer (401, 404, etc.)
        raise e

    except Exception:
        request_id = str(uuid4())
        logger.exception("[%s] ERROR request_id=%s", module_name, request_id)

        # 👉 IMPORTANT: on garde un code HTTP clair
        raise HTTPException(
            status_code=500,
            detail={
                "module": module_name,
                "message": "Internal Server Error",
                "error": "unexpected_error",
                "request_id": request_id,
            },
        )
