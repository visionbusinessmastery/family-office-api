"""
Canonical Ethan Core entrypoint.

Backend source of truth rule:
- Ethan Core is the only conversational cognition entrypoint.
- Routes and frontend components call this facade instead of rebuilding advice.
- Satellite modules may compute or simulate, but they do not decide.
"""

from advisor.ethan.response_engine import CORE_EMPTY_STATUS, with_core_contract
from advisor.service import advisor_logic


def run_ethan_core(user_email: str, message: str, *, mode: str = "chat", bypass_cache: bool = False):
    """
    Run Ethan's canonical backend cognition flow.

    The existing advisor service remains the implementation engine for V4.9.9;
    this facade centralizes every route connection before deeper cleanup.
    """
    cleaned_message = (message or "").strip()
    if not cleaned_message:
        return with_core_contract({"status": CORE_EMPTY_STATUS, "analysis": ""}, mode)

    if mode == "portfolio":
        cleaned_message = f"Analyse portefeuille: {cleaned_message}"

    result = advisor_logic(
        user_email,
        cleaned_message,
        bypass_cache=bypass_cache,
    )
    return with_core_contract(result, mode)


def run_ethan_chat(user_email: str, message: str, *, bypass_cache: bool = False):
    return run_ethan_core(
        user_email,
        message,
        mode="chat",
        bypass_cache=bypass_cache,
    )
