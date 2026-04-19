import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def calculate_ai_score(sentiment_score, trend_score, price_change, pe_ratio=None):

    score = 50  # base neutre

    # =========================
    # SENTIMENT (30%)
    # =========================
    score += (sentiment_score - 50) * 0.3

    # =========================
    # TREND (25%)
    # =========================
    score += (trend_score - 50) * 0.25

    # =========================
    # MOMENTUM (25%)
    # =========================
    try:
        change = float(price_change)

        if change > 5:
            score += 15
        elif change > 2:
            score += 8
        elif change < -5:
            score -= 15
        elif change < -2:
            score -= 8
    except Exception:
        pass

    # =========================
    # FUNDAMENTAL (20%)
    # =========================
    if pe_ratio:
        try:
            pe = float(pe_ratio)

            if 0 < pe < 20:
                score += 10
            elif pe > 40:
                score -= 10
        except Exception:
            pass

    # clamp 0-100
    return max(0, min(100, round(score, 2)))

def get_signal(score):

    if score >= 70:
        return "BUY"
    elif score >= 50:
        return "HOLD"
    else:
        return "SELL"

def get_risk(score):

    if score >= 70:
        return "LOW"
    elif score >= 40:
        return "MEDIUM"
    else:
        return "HIGH"

def global_score(return_rate, risk, duration):
    score = 0

    score += return_rate * 2

    if risk == "low":
        score += 20
    elif risk == "medium":
        score += 10

    if duration < 24:
        score += 10

    return min(score, 100)
