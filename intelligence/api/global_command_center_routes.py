from fastapi import APIRouter

from intelligence.api.global_command_center import (
    compute_global_command_center
)

router = APIRouter(
    prefix="/global-command-center",
    tags=["Global Command Center"]
)

@router.get("/")
def global_command_center():

    result = compute_global_command_center(
        user={},
        onboarding={},
        portfolio={},
        financial_overview={}
    )

    return result
