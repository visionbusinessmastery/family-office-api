from advisor.autopilot_v4_engine import get_autopilot_v4
from advisor.ethan.context_engine import compact_portfolio
from auth.utils import get_user_id
from database import engine
from portfolio.service import get_user_portfolio


def run_autopilot_safely(user_email, portfolio, market, context, llm_text, level):
    try:
        autopilot = get_autopilot_v4()
        return autopilot.run(
            user_email=user_email,
            portfolio=portfolio,
            market=market,
            context=context,
            llm_analysis=llm_text,
            level=level,
        )
    except Exception as e:
        return {"status": "unavailable", "message": str(e)}


def portfolio_autopilot(user_email, message):
    user_id = None

    with engine.connect() as conn:
        user_id = get_user_id(conn, user_email)

    return run_autopilot_safely(
        user_email=user_email,
        portfolio=compact_portfolio(get_user_portfolio(user_id) if user_id else {}),
        market={},
        context={},
        llm_text=None,
        level="free",
    )
