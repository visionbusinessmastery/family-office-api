# =========================
# SCORING REGISTRY (SOURCE OF TRUTH)
# =========================

from modules.business.scoring import business_score
from modules.crypto.scoring import crypto_score
from modules.real_estate.scoring import real_estate_score
from modules.banking.scoring import banking_score
from modules.market.scoring import market_score

from modules.stocks.scoring import stocks_score
from modules.startup.scoring import startup_score
from modules.private_equity.scoring import private_equity_score
from modules.franchise.scoring import franchise_score
from modules.etf.scoring import etf_score
from modules.entrepreneurship.scoring import entrepreneurship_score
from modules.crowdfunding.scoring import crowdfunding_score
from modules.commodities.scoring import commodities_score
from modules.ai_business.scoring import ai_business_score

SCORING_ENGINES = {
    "business": business_score,
    "crypto": crypto_score,
    "real_estate": real_estate_score,
    "banking": banking_score,
    "market": market_score,

    "stocks": stocks_score,

    "startup": startup_score,
    "private_equity": private_equity_score,
    "franchise": franchise_score,
    "etf": etf_score,
    "entrepreneurship": entrepreneurship_score,
    "crowdfunding": crowdfunding_score,
    "commodities": commodities_score,
    "ai_business": ai_business_score,
}
