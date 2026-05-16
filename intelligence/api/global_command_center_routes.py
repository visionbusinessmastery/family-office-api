from fastapi import APIRouter

from intelligence.api.global_command_center import (
    compute_global_command_center
)

# =========================
# ROUTER
# =========================
router = APIRouter(
    tags=["Global Command Center"]
)

# =========================
# GLOBAL COMMAND CENTER
# =========================
@router.get("/")
def global_command_center():

    result = compute_global_command_center(
        user={},
        onboarding={},
        portfolio=[],
        financial_overview={}
    )

    return result
