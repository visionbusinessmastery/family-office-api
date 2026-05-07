# =========================
# AFFILIATE REGISTRY
# =========================

from modules.business.affiliate_engine import (
    get_business_affiliates
)

from modules.banking.affiliate_engine import (
    get_banking_affiliates
)

from modules.market.affiliate_engine import (
    get_market_affiliates
)

from modules.stocks.affiliate_engine import (
    get_stocks_affiliates
)

AFFILIATE_ENGINES = {

    "business": get_business_affiliates,
    "banking": get_banking_affiliates,
    "market": get_market_affiliates,
    "stocks": get_stocks_affiliates,
}
