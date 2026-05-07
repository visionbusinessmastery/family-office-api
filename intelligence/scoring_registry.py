# =========================
# SCORING REGISTRY
# =========================

from modules.business.scoring import business_score
from modules.crypto.scoring import crypto_score
from modules.real_estate.scoring import real_estate_score
from modules.banking.scoring import banking_score
from modules.market.scoring import market_score
from modules.stocks.scoring import stocks_score

SCORING_ENGINES = {

    "business": business_score,
    "crypto": crypto_score,
    "real_estate": real_estate_score,
    "banking": banking_score,
    "market": market_score,
    "stocks": stocks_score,
}
