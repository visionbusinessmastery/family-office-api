import logging
from fastapi import HTTPException

def safe_execute(func, data=None, module_name=""):
    try:
        return func(data) if data else func()

    except HTTPException as e:
        # 🔥 Laisse FastAPI gérer les erreurs propres (401, 404, etc.)
        raise e

    except Exception as e:
        logging.error(f"{module_name} ERROR: {str(e)}")

        return {
            "status": "error",
            "module": module_name,
            "message": "Erreur interne serveur",
            "details": str(e)
        }
