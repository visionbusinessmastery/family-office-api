import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from database import Base, engine
from core.limiter import limiter
from auth.utils import decode_token

# =========================
# ROUTERS IMPORT
# =========================
from auth.routes import router as auth_router
from advisor.routes import router as advisor_router
from advisor.service import ensure_ethan_ai_tables
from billing.routes import router as billing_router, ensure_billing_tables
from product.routes import router as product_router, ensure_product_tables
from profile.routes import router as profile_router, ensure_profile_tables
from referrals.routes import router as referrals_router, ensure_referral_tables
from workspaces.routes import router as workspaces_router, ensure_workspace_tables
from legacy.routes import router as legacy_router, ensure_legacy_tables

from intelligence.routes import router as intelligence_router
from intelligence.category_opportunities import router as category_opportunities_router
from intelligence.opportunity_intelligence import (
    ensure_opportunity_intelligence_tables,
    router as opportunity_intelligence_router,
)
from intelligence.routes_finance import router as finance_router
from intelligence.routes_score import router as intelligence_score_router
from intelligence.routes_onboarding import router as onboarding_router

from market.routes import router as market_router
from portfolio.routes import router as portfolio_router
from portfolio.service import ensure_portfolio_schema
from portfolio.real_estate_routes import (
    router as real_estate_router,
    ensure_real_estate_table,
)
from portfolio.specialized_assets_routes import (
    router as specialized_assets_router,
    ensure_venture_table,
    ensure_yield_table,
)
from stocks.routes import router as stocks_router

from intelligence.gamification.api.dashboard import router as gamification_router

from intelligence.api.global_command_center_routes import (
    router as global_command_center_router
)


# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logging.info("APP STARTING")

# =========================
# LIFESPAN
# =========================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("DB INIT START")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        ensure_workspace_tables(conn)
        ensure_portfolio_schema(conn)
        ensure_real_estate_table(conn)
        ensure_yield_table(conn)
        ensure_venture_table(conn)
        ensure_product_tables(conn)
        ensure_billing_tables(conn)
        ensure_profile_tables(conn)
        ensure_referral_tables(conn)
        ensure_legacy_tables(conn)
        ensure_ethan_ai_tables(conn)
        ensure_opportunity_intelligence_tables(conn)
    logging.info("DB INIT OK")
    yield


# =========================
# APP INIT (SINGLE SOURCE OF TRUTH)
# =========================
app = FastAPI(
    title="WHITE ROCK Wealth OS",
    version="4.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter

logging.info("LIMITER OK")

# =========================
# CORS (FIX IMPORTANT)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://family-office-api-n4sv.onrender.com",
        "https://vision-business.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ERROR HANDLERS
# =========================
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"status": "error", "message": "Too many requests"},
    )

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logging.error(f"ERROR: {str(exc)}")

    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )

# =========================
# AUTH MIDDLEWARE
# =========================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):

    try:
        token = request.headers.get("Authorization")

        if token:
            token = token.replace("Bearer ", "")
            try:
                request.state.user_email = decode_token(token)
            except Exception as e:
                logging.error(f"TOKEN ERROR: {str(e)}")
                request.state.user_email = "anonymous"
        else:
            request.state.user_email = "anonymous"

    except Exception as e:
        logging.error(f"MIDDLEWARE ERROR: {str(e)}")
        request.state.user_email = "anonymous"

    response = await call_next(request)
    return response


logging.info("AUTH OK")

# =========================
# ROUTES
# =========================
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(advisor_router, prefix="/advisor", tags=["Advisor"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
app.include_router(product_router, prefix="/product", tags=["Product"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])
app.include_router(referrals_router, prefix="/referrals", tags=["Referrals"])
app.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
app.include_router(legacy_router, prefix="/legacy", tags=["Legacy"])

app.include_router(intelligence_router, prefix="/intelligence", tags=["Intelligence"])
app.include_router(category_opportunities_router, prefix="/intelligence", tags=["Opportunities"])
app.include_router(opportunity_intelligence_router, prefix="/intelligence", tags=["Opportunities"])
app.include_router(finance_router, prefix="/finance", tags=["Finance"])
app.include_router(intelligence_score_router, prefix="/intelligence", tags=["Score"])
app.include_router(onboarding_router)

app.include_router(gamification_router, prefix="/gamification", tags=["Gamification"])

app.include_router(market_router, prefix="/market", tags=["Market"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(real_estate_router, prefix="/real-estate", tags=["Real Estate"])
app.include_router(specialized_assets_router, tags=["Specialized Assets"])
app.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])

app.include_router(
    global_command_center_router,
    prefix="/global-command-center",
    tags=["Global AI"]
)

logging.info("ROUTERS OK")

# =========================
# HEALTH
# =========================
@app.get("/")
def root():
    return {
        "status": "WHITE ROCK WEALTH OS ONLINE",
        "architecture": "clean_v4"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "modules": [
            "advisor",
            "intelligence",
            "finance",
            "score",
            "market",
            "portfolio",
            "real_estate",
            "stocks",
            "global_command_center",
            "gamification",
            "legacy"
        ]
    }

@app.get("/info")
def info():
    return {
        "app": "WHITE ROCK Wealth OS",
        "version": "4.0",
        "status": "production_ready"
    }

logging.info("MAIN LOADED SUCCESSFULLY")
