import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from core.limiter import limiter
from auth.utils import decode_token

# =========================
# ROUTES CORE V4 ONLY
# =========================
from auth.routes import router as auth_router
from advisor.routes import router as advisor_router
from intelligence.routes import router as intelligence_router
from intelligence.routes_finance import router as finance_router
from intelligence.routes_score import router as score_router
from market.routes import router as market_router
from portfolio.routes import router as portfolio_router
from stocks.routes import router as stocks_router

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# =========================
# APP INIT
# =========================
app = FastAPI(
    title="AI Family Office V4",
    version="4.0.0"
)

app.state.limiter = limiter

# =========================
# CORS CLEAN
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
# ERROR HANDLING
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
# STARTUP
# =========================
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

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
            except Exception:
                request.state.user_email = "anonymous"
        else:
            request.state.user_email = "anonymous"

    except Exception:
        request.state.user_email = "anonymous"

    return await call_next(request)

# =========================
# ROUTES V4 CLEAN
# =========================
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(advisor_router, prefix="/advisor", tags=["Advisor"])
app.include_router(intelligence_router, prefix="/intelligence", tags=["Intelligence"])
app.include_router(finance_router, prefix="/finance", tags=["Finance"])
app.include_router(score_router, prefix="/score", tags=["Score"])

app.include_router(market_router, prefix="/market", tags=["Market"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(stocks_router, prefix="/stocks", tags=["Stocks"])

# =========================
# HEALTH
# =========================
@app.get("/")
def root():
    return {
        "status": "AI FAMILY OFFICE V4 ONLINE",
        "architecture": "clean_v4"
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "modules": ["advisor", "intelligence", "finance", "score"]
    }

@app.get("/info")
def info():
    return {
        "app": "Family Office AI",
        "version": "4.0",
        "status": "production_ready"
    }
