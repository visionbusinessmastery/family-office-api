# =========================
# GLOBAL COMMAND CENTER ROUTE
# =========================

# =========================
# IMPORTS
# =========================
from fastapi import APIRouter, Request

from core.utils import safe_execute
from intelligence.routes import build_command_center_payload

# =========================
# ROUTER
# =========================
router = APIRouter(
    tags=["Global Command Center"]
)

# =========================
# GLOBAL COMMAND CENTER (FRONTEND ENTRYPOINT)
# =========================
@router.get("/")
def global_command_center(request: Request):

    def _run():
        return build_command_center_payload(request.state.user_email)

    return safe_execute(_run, module_name="GLOBAL_COMMAND_CENTER")
