import logging
from fastapi import HTTPException


# =========================
# SAFE EXECUTOR (PRODUCTION SAFE)
# =========================
def safe_execute(func, data=None, module_name=""):

    try:
        return func(data) if data else func()

    except HTTPException as e:
        # 👉 Laisse FastAPI gérer (401, 404, etc.)
        raise e

    except Exception as e:

        logging.exception(f"[{module_name}] ERROR")

        # 👉 IMPORTANT: on garde un code HTTP clair
        raise HTTPException(
            status_code=500,
            detail={
                "module": module_name,
                "message": "Internal Server Error",
                "error": str(e)
            }
        )
