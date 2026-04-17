from core.limiter import limiter
from core.utils import safe_execute
from fastapi import APIRouter, Request, Query
from .schemas import MarketRequest
from .service import get_market, get_market_intelligence

router = APIRouter()

# =========================
# MARKET SIMPLE
# =========================
@router.post("/market")
@limiter.limit("20/minute")
def market(request: Request, data: MarketRequest):

    def _market():
        user_email = request.state.user_email

        result = get_market(data.query)

        return {
            "user": user_email,
            "query": data.query,
            "market": result
        }

    return safe_execute(_market, module_name="MARKET")


# =========================
# MARKET INTELLIGENCE
# =========================
@router.get("/market-intelligence")
@limiter.limit("20/minute")
def market_intelligence(request: Request, query: str = Query(...)):

    def _market_intelligence():
        user_email = request.state.user_email

        result = get_market_intelligence(query)

        return {
            "user": user_email,
            "query": query,
            "results": result
        }

    return safe_execute(_market_intelligence, module_name="MARKET_INTELLIGENCE")
