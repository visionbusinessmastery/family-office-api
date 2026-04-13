import logging

def safe_execute(func, data=None, module_name=""):
    try:
        if data:
            return func(data)
        else:
            return func()

    except Exception as e:
        logging.error(f"{module_name} ERROR: {str(e)}")

        return {
            "status": "error",
            "module": module_name,
            "message": "Une erreur est survenue",
            "details": str(e)
        }
