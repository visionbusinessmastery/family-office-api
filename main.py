import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from advisor.routes import router as advisor_router
from ai.routes import router as ai_router
from alerts.routes import router as alerts_router
from auth.routes import router as auth_router
from auth.utils import decode_token
from business.routes import router as business_router
from content.routes import router as content_router
from core.limiter import limiter
from crm.routes import router as crm_router
from crypto.routes import router as crypto_router
from crowdfunding.routes import router as crowdfunding_router
from database import Base, engine
from franchise.routes import router as franchise_router
from intelligence.routes import router as intelligence_router
from market.routes import router as market_router
from portfolio.routes import router as portfolio_router
from real_estate.routes import router as real_router
from stocks.routes import router as stocks_router
from trading.routes import router as trading_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Family Office AI", version="10.1")

app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ton-frontend.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "status": "error",
            "message": "Trop de requêtes, ralentis",
        },
    )


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "API Family Office running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modules": ["advisor", "alerts", "trading", "portfolio", "market"],
    }


@app.get("/info")
def info():
    return {
        "app": "Family Office AI",
        "version": "10.1",
        "status": "running",
    }


@app.middleware("http")
async def add_user_to_request(request: Request, call_next):
    try:
        token = request.headers.get("Authorization")
        if token:
            token = token.replace("Bearer ", "")
            request.state.user_email = decode_token(token)
        else:
            request.state.user_email = "anonymous"
    except Exception:
        request.state.user_email = "anonymous"

    response = await call_next(request)
    return response


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(market_router, prefix="/market", tags=["Market"])
app.include_router(real_router, prefix="/real", tags=["Real"])
app.include_router(business_router, prefix="/business", tags=["Business"])
app.include_router(franchise_router, prefix="/franchise", tags=["Franchise"])
app.include_router(crypto_router, prefix="/crypto", tags=["Crypto"])
app.include_router(crowdfunding_router, prefix="/crowdfunding", tags=["Crowdfunding"])
app.include_router(intelligence_router, prefix="/intelligence", tags=["Global Intelligence"])
app.include_router(advisor_router, prefix="/advisor", tags=["ADVISOR"])
app.include_router(alerts_router, prefix="/alerts", tags=["ALERTS"])
app.include_router(trading_router, prefix="/trading", tags=["TRADING"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])
app.include_router(crm_router, prefix="/crm", tags=["CRM"])
app.include_router(content_router)







