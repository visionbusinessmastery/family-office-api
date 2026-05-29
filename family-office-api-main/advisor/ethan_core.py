"""
Canonical Ethan Core entrypoint.

Backend source of truth rule:
- Ethan Core is the only conversational cognition entrypoint.
- Routes and frontend components call this facade instead of rebuilding advice.
- Satellite modules may compute or simulate, but they do not decide.
"""

from advisor.service import advisor_logic


ETHAN_CORE_SYSTEM = "ETHAN_CORE_V4"


def _with_core_contract(result, mode: str):
    if not isinstance(result, dict):
        return result

    next_result = dict(result)
    next_result["source"] = "ethan_core"
    next_result["mode"] = mode
    next_result["system"] = ETHAN_CORE_SYSTEM
    return next_result


def run_ethan_core(user_email: str, message: str, *, mode: str = "chat", bypass_cache: bool = False):
    """
    Run Ethan's canonical backend cognition flow.

    The existing advisor service remains the implementation engine for V4.9.9;
    this facade centralizes every route connection before deeper cleanup.
    """
    cleaned_message = (message or "").strip()

    if mode == "portfolio":
        cleaned_message = f"Analyse portefeuille: {cleaned_message}"

    result = advisor_logic(
        user_email,
        cleaned_message,
        bypass_cache=bypass_cache,
    )
    return _with_core_contract(result, mode)


def run_ethan_chat(user_email: str, message: str, *, bypass_cache: bool = False):
    return run_ethan_core(
        user_email,
        message,
        mode="chat",
        bypass_cache=bypass_cache,
    )


def run_ethan_portfolio(user_email: str, message: str, *, bypass_cache: bool = False):
    return run_ethan_core(
        user_email,
        message,
        mode="portfolio",
        bypass_cache=bypass_cache,
    )
