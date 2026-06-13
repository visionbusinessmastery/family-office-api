# =========================
# AFFILIATE REGISTRY
# =========================

from modules.ai_business.affiliate_engine import get_ai_business_affiliates
from modules.banking.affiliate_engine import get_banking_affiliates
from modules.business.affiliate_engine import get_business_affiliates
from modules.commodities.affiliate_engine import get_commodities_affiliates
from modules.crowdfunding.affiliate_engine import get_crowdfunding_affiliates
from modules.crypto.affiliate_engine import get_crypto_affiliates
from modules.etf.affiliate_engine import get_etf_affiliates
from modules.franchise.affiliate_engine import get_franchise_affiliates
from modules.market.affiliate_engine import get_market_affiliates
from modules.private_equity.affiliate_engine import get_private_equity_affiliates
from modules.real_estate.affiliate_engine import get_real_estate_affiliates
from modules.startup.affiliate_engine import get_startup_affiliates
from modules.stocks.affiliate_engine import get_stock_affiliates
from modules.trading.affiliate_engine import get_trading_affiliates


AFFILIATE_ENGINES = {
    "ai_business": get_ai_business_affiliates,
    "banking": get_banking_affiliates,
    "business": get_business_affiliates,
    "commodities": get_commodities_affiliates,
    "crowdfunding": get_crowdfunding_affiliates,
    "crypto": get_crypto_affiliates,
    "etf": get_etf_affiliates,
    "franchise": get_franchise_affiliates,
    "market": get_market_affiliates,
    "private_equity": get_private_equity_affiliates,
    "real_estate": get_real_estate_affiliates,
    "startup": get_startup_affiliates,
    "stocks": get_stock_affiliates,
    "trading": get_trading_affiliates,
}
