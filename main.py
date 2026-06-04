from dotenv import load_dotenv
load_dotenv()

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from database import Base, engine
from core.limiter import limiter
from auth.utils import decode_token
from security.audit import ensure_security_tables
from security.middleware import security_middleware
from security.routes import router as security_router
from monitoring.sentry_config import capture_exception, init_sentry
from monitoring.health import check_cache, check_db, check_openai, check_stripe, system_health
from monitoring.routes import router as monitoring_router
from analytics.posthog_service import ensure_analytics_tables
from feature_flags.engine import ensure_feature_flags_table
from feature_flags.routes import router as feature_flags_router



PUBLIC_PATHS = {
    "/",
    "/health",
    "/health/db",
    "/health/openai",
    "/health/stripe",
    "/health/cache",
    "/info",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/auth/register",
    "/auth/login",
    "/auth/verify-email",
    "/auth/set-password",
    "/auth/oauth/providers",
    "/auth/oauth/session",
    "/billing/plans",
    "/billing/config",
    "/billing/webhook",
    "/privacy/region",
    "/privacy/cookie-consent",
    "/referrals/track",
}

PUBLIC_PREFIXES = (
    "/auth/oauth/session/",
    "/privacy/delete-account/confirm/",
)


def is_public_path(path: str) -> bool:
    normalized_path = "/" + path.strip("/")
    if normalized_path == "/":
        normalized_path = "/"

    if normalized_path in PUBLIC_PATHS or any(normalized_path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return True

    parts = normalized_path.strip("/").split("/")
    return (
        len(parts) == 4
        and parts[0] == "auth"
        and parts[1] == "oauth"
        and parts[3] in {"start", "callback"}
    )


def extract_bearer_token(header_value: str | None) -> str | None:
    if not header_value:
        return None

    parts = header_value.strip().split()
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1]:
        return parts[1]

    return None

# =========================
# ROUTERS IMPORT
# =========================
from auth.routes import router as auth_router
from auth.oauth import router as oauth_router, ensure_oauth_tables
from advisor.routes import router as advisor_router
from advisor.service import ensure_ethan_ai_tables
from billing.routes import router as billing_router, ensure_billing_tables
from product.routes import router as product_router, ensure_product_tables
from profile.routes import router as profile_router, ensure_profile_tables
from privacy.routes import (
    ensure_privacy_tables,
    profile_router as privacy_profile_router,
    router as privacy_router,
)
from referrals.routes import router as referrals_router, ensure_referral_tables
from workspaces.routes import router as workspaces_router, ensure_workspace_tables
from legacy.routes import router as legacy_router, ensure_legacy_tables

from intelligence.routes import router as intelligence_router
from intelligence.category_opportunities import router as category_opportunities_router
from intelligence.opportunity_intelligence import (
    ensure_opportunity_intelligence_tables,
    router as opportunity_intelligence_router,
)
from intelligence.weekly_report_service import (
    ensure_weekly_report_tables,
    router as weekly_report_router,
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
        ensure_privacy_tables(conn)
        ensure_security_tables(conn)
        ensure_analytics_tables(conn)
        ensure_feature_flags_table(conn)
        ensure_oauth_tables(conn)
        ensure_referral_tables(conn)
        ensure_legacy_tables(conn)
        ensure_ethan_ai_tables(conn)
        ensure_opportunity_intelligence_tables(conn)
        ensure_weekly_report_tables(conn)
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

init_sentry(app)

app.state.limiter = limiter

logging.info("LIMITER OK")

app.middleware("http")(security_middleware)

# =========================
# CORS (FIX IMPORTANT)
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://family-office-api-n4sv.onrender.com",
        "https://vision-business.com",
        "https://family-office-front.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# CSP FIX (Swagger /docs Render)
# =========================
@app.middleware("http")
async def csp_fix_middleware(request: Request, call_next):
    response = await call_next(request)

    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://js.stripe.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' https: data:; "
        "connect-src 'self' https:;"
    )

    return response

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
    capture_exception(exc, {"path": str(request.url.path)})

    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal Server Error"},
    )

# =========================
# AUTH MIDDLEWARE
# =========================
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    request.state.user_email = None
    request.state.auth_error = None

    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    public_path = is_public_path(path)

    token = extract_bearer_token(request.headers.get("Authorization"))

    email = None

    if token:
        try:
            email = decode_token(token)
        except Exception as e:
            logging.warning("AUTH TOKEN REJECTED: %s", str(e))
            request.state.auth_error = "invalid_token"

            if not public_path:
                return JSONResponse(status_code=401, content={"detail": "Token invalide"})

    if not email and not public_path:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentification requise"},
        )

    request.state.user_email = email or "anonymous"

    return await call_next(request)


logging.info("AUTH OK")

# =========================
# ROUTES
# =========================
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(oauth_router, prefix="/auth/oauth", tags=["OAuth"])
app.include_router(advisor_router, prefix="/advisor", tags=["Advisor"])
app.include_router(billing_router, prefix="/billing", tags=["Billing"])
app.include_router(product_router, prefix="/product", tags=["Product"])
app.include_router(profile_router, prefix="/profile", tags=["Profile"])
app.include_router(privacy_profile_router, prefix="/profile", tags=["Privacy"])
app.include_router(privacy_router, prefix="/privacy", tags=["Privacy"])
app.include_router(security_router, prefix="/security", tags=["Security"])
app.include_router(monitoring_router, prefix="/system", tags=["System"])
app.include_router(feature_flags_router, prefix="/feature-flags", tags=["Feature Flags"])
app.include_router(referrals_router, prefix="/referrals", tags=["Referrals"])
app.include_router(workspaces_router, prefix="/workspaces", tags=["Workspaces"])
app.include_router(legacy_router, prefix="/legacy", tags=["Legacy"])

app.include_router(intelligence_router, prefix="/intelligence", tags=["Intelligence"])
app.include_router(category_opportunities_router, prefix="/intelligence", tags=["Opportunities"])
app.include_router(opportunity_intelligence_router, prefix="/intelligence", tags=["Opportunities"])
app.include_router(weekly_report_router, prefix="/intelligence", tags=["Reports"])
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
    return system_health()


@app.get("/health/db")
def health_db():
    return check_db()


@app.get("/health/openai")
def health_openai(live: bool = False):
    return check_openai(live=live)


@app.get("/health/stripe")
def health_stripe():
    return check_stripe()


@app.get("/health/cache")
def health_cache():
    return check_cache()

@app.get("/info")
def info():
    return {
        "app": "WHITE ROCK Wealth OS",
        "version": "4.0",
        "status": "production_ready"
    }

logging.info("MAIN LOADED SUCCESSFULLY")
