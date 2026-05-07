# =========================
# MODULE REGISTRY
# =========================

# CORE MODULES
from modules.business.opportunity_engine import get_business_opportunities
from modules.crypto.opportunity_engine import get_crypto_opportunities
from modules.real_estate.opportunity_engine import get_real_estate_opportunities
from modules.crowdfunding.opportunity_engine import get_crowdfunding_opportunities
from modules.franchise.opportunity_engine import get_franchise_opportunities
from modules.trading.opportunity_engine import get_trading_opportunities

# MARKET MODULES
from modules.market.opportunity_engine import get_market_opportunities
from modules.stocks.opportunity_engine import get_stock_opportunities
from modules.etf.opportunity_engine import get_etf_opportunities
from modules.commodities.opportunity_engine import get_commodities_opportunities

# BUSINESS / WEALTH
from modules.ai_business.opportunity_engine import get_ai_business_opportunities
from modules.startup.opportunity_engine import get_startup_opportunities
from modules.private_equity.opportunity_engine import get_private_equity_opportunities
from modules.wealth.opportunity_engine import get_wealth_opportunities
from modules.entrepreneurship.opportunity_engine import (
    get_entrepreneurship_opportunities
)

# BANKING
from modules.banking.opportunity_engine import get_banking_opportunities


# =========================
# CENTRAL REGISTRY
# =========================
MODULES = {

    # =========================
    # CORE MARKETS
    # =========================
    "market": get_market_opportunities,
    "stocks": get_stock_opportunities,
    "crypto": get_crypto_opportunities,
    "etf": get_etf_opportunities,
    "commodities": get_commodities_opportunities,

    # =========================
    # REAL ASSETS
    # =========================
    "real_estate": get_real_estate_opportunities,
    "crowdfunding": get_crowdfunding_opportunities,
    "franchise": get_franchise_opportunities,
    "private_equity": get_private_equity_opportunities,

    # =========================
    # BUSINESS
    # =========================
    "business": get_business_opportunities,
    "ai_business": get_ai_business_opportunities,
    "startup": get_startup_opportunities,
    "entrepreneurship": get_entrepreneurship_opportunities,

    # =========================
    # TRADING
    # =========================
    "trading": get_trading_opportunities,

    # =========================
    # BANKING / WEALTH
    # =========================
    "banking": get_banking_opportunities,
    "wealth": get_wealth_opportunities,
}
