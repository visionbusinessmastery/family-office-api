import requests
from config import FMP_API_KEY
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
    except:
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
        except:
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



