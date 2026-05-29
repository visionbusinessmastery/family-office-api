import hashlib
import json
import os

from advisor.ethan.cache_policy import ETHAN_GLOBAL_CACHE_VERSION
from product.entitlements import normalize_plan, plan_allows


ADVISOR_CACHE_VERSION = ETHAN_GLOBAL_CACHE_VERSION

MODEL_LIGHT = os.getenv("ETHAN_MODEL_LIGHT", "gpt-5-nano")
MODEL_STANDARD = os.getenv("ETHAN_MODEL_STANDARD", "gpt-5-mini")
MODEL_PREMIUM = os.getenv("ETHAN_MODEL_PREMIUM", "gpt-5")
MODEL_DYNASTY = os.getenv("ETHAN_MODEL_DYNASTY", MODEL_PREMIUM)
MODEL_FALLBACK = os.getenv("ETHAN_MODEL_FALLBACK", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))

ESTIMATED_INPUT_COST = {
    MODEL_LIGHT: float(os.getenv("ETHAN_LIGHT_INPUT_COST_PER_1M", "0.05")),
    MODEL_STANDARD: float(os.getenv("ETHAN_STANDARD_INPUT_COST_PER_1M", "0.25")),
    MODEL_PREMIUM: float(os.getenv("ETHAN_PREMIUM_INPUT_COST_PER_1M", "1.25")),
    MODEL_DYNASTY: float(os.getenv("ETHAN_DYNASTY_INPUT_COST_PER_1M", "1.25")),
}

ESTIMATED_OUTPUT_COST = {
    MODEL_LIGHT: float(os.getenv("ETHAN_LIGHT_OUTPUT_COST_PER_1M", "0.4")),
    MODEL_STANDARD: float(os.getenv("ETHAN_STANDARD_OUTPUT_COST_PER_1M", "2.0")),
    MODEL_PREMIUM: float(os.getenv("ETHAN_PREMIUM_OUTPUT_COST_PER_1M", "10.0")),
    MODEL_DYNASTY: float(os.getenv("ETHAN_DYNASTY_OUTPUT_COST_PER_1M", "10.0")),
}

PLAN_CONFIG = {
    "FREE": {
        "tier": "ESSENTIALS",
        "max_output_tokens": 220,
        "daily_deep_sessions": 0,
        "default_model": MODEL_LIGHT,
    },
    "GOLD": {
        "tier": "GROWTH",
        "max_output_tokens": 420,
        "daily_deep_sessions": 1,
        "default_model": MODEL_STANDARD,
    },
    "ELITE": {
        "tier": "STRATEGIST",
        "max_output_tokens": 650,
        "daily_deep_sessions": 3,
        "default_model": MODEL_STANDARD,
    },
    "LIBERTY": {
        "tier": "EXECUTIVE",
        "max_output_tokens": 800,
        "daily_deep_sessions": 6,
        "default_model": MODEL_PREMIUM,
    },
    "LEGACY": {
        "tier": "DYNASTY",
        "max_output_tokens": 900,
        "daily_deep_sessions": 10,
        "default_model": MODEL_DYNASTY,
    },
}

LOW_KEYWORDS = [
    "bonjour",
    "merci",
    "resume",
    "rappel",
    "motivation",
    "simple",
    "rapide",
    "action du jour",
]

MEDIUM_KEYWORDS = [
    "portfolio",
    "portefeuille",
    "budget",
    "diversification",
    "immobilier",
    "crypto",
    "etf",
    "forex",
    "opportunite",
    "capital",
]

HIGH_KEYWORDS = [
    "fiscal",
    "trust",
    "holding",
    "succession",
    "transmission",
    "gouvernance",
    "legacy",
    "heritage",
    "simulation",
    "architecture patrimoniale",
    "strategie internationale",
]


def stable_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def estimate_tokens(text_value):
    return max(1, int(len(text_value or "") / 4))


def estimate_cost(model, input_tokens, output_tokens):
    input_cost = ESTIMATED_INPUT_COST.get(model, ESTIMATED_INPUT_COST.get(MODEL_STANDARD, 0))
    output_cost = ESTIMATED_OUTPUT_COST.get(model, ESTIMATED_OUTPUT_COST.get(MODEL_STANDARD, 0))
    return round((input_tokens / 1_000_000) * input_cost + (output_tokens / 1_000_000) * output_cost, 8)


def classify_request(message):
    normalized = (message or "").lower()

    if any(keyword in normalized for keyword in HIGH_KEYWORDS):
        return "high"

    if len(normalized) > 420:
        return "high"

    if any(keyword in normalized for keyword in MEDIUM_KEYWORDS):
        return "medium"

    if len(normalized) < 160 or any(keyword in normalized for keyword in LOW_KEYWORDS):
        return "low"

    return "medium"


def classify_task(message, complexity):
    normalized = (message or "").lower()

    if complexity == "high":
        return "strategic_analysis"
    if any(word in normalized for word in ["portfolio", "portefeuille", "allocation", "diversification"]):
        return "portfolio_guidance"
    if any(word in normalized for word in ["budget", "charge", "revenu", "cashflow"]):
        return "financial_guidance"
    if any(word in normalized for word in ["succession", "heritage", "legacy", "transmission"]):
        return "legacy_guidance"
    return "conversation"


def choose_model(plan, complexity, deep_sessions_used):
    normalized_plan = normalize_plan(plan)
    config = PLAN_CONFIG[normalized_plan]
    soft_budget_active = False

    if complexity == "low":
        model = MODEL_LIGHT
    elif complexity == "medium":
        model = MODEL_STANDARD
    else:
        if config["daily_deep_sessions"] <= deep_sessions_used:
            model = MODEL_STANDARD if plan_allows(normalized_plan, "GOLD") else MODEL_LIGHT
            soft_budget_active = True
        elif plan_allows(normalized_plan, "LIBERTY"):
            model = config["default_model"]
        elif plan_allows(normalized_plan, "ELITE"):
            model = MODEL_PREMIUM
        else:
            model = MODEL_STANDARD

    return model, soft_budget_active


def build_advisor_cache_hash(user_email, message, plan, complexity, fingerprint):
    raw = {
        "version": ADVISOR_CACHE_VERSION,
        "email": user_email,
        "message": message.strip().lower(),
        "plan": plan,
        "complexity": complexity,
        "fingerprint": fingerprint,
    }
    return stable_hash(raw)
