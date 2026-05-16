# =========================
# SCORING REGISTRY V2
# SOURCE OF TRUTH
# =========================

from modules.business.scoring import (
    business_score
)

from modules.crypto.scoring import (
    crypto_score
)

from modules.real_estate.scoring import (
    real_estate_score
)

from modules.banking.scoring import (
    banking_score
)

from modules.market.scoring import (
    market_score
)

from modules.stocks.scoring import (
    stocks_score
)

from modules.startup.scoring import (
    startup_score
)

from modules.private_equity.scoring import (
    private_equity_score
)

from modules.franchise.scoring import (
    franchise_score
)

from modules.etf.scoring import (
    etf_score
)

from modules.entrepreneurship.scoring import (
    entrepreneurship_score
)

from modules.crowdfunding.scoring import (
    crowdfunding_score
)

from modules.commodities.scoring import (
    commodities_score
)

from modules.ai_business.scoring import (
    ai_business_score
)


# =========================
# REGISTRY
# =========================
SCORING_ENGINES = {

    # =========================
    # CORE MODULES
    # =========================
    "business": {

        "engine":
            business_score,

        "category":
            "business",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.2,

        "label":
            "Business",

        "description":
            "Business & entrepreneurship scoring",
    },

    "crypto": {

        "engine":
            crypto_score,

        "category":
            "investing",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            0.9,

        "label":
            "Crypto",

        "description":
            "Crypto asset scoring",
    },

    "real_estate": {

        "engine":
            real_estate_score,

        "category":
            "real_estate",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.3,

        "label":
            "Real Estate",

        "description":
            "Property investment scoring",
    },

    "banking": {

        "engine":
            banking_score,

        "category":
            "finance",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.0,

        "label":
            "Banking",

        "description":
            "Banking & savings scoring",
    },

    "market": {

        "engine":
            market_score,

        "category":
            "markets",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.0,

        "label":
            "Markets",

        "description":
            "Global markets scoring",
    },

    # =========================
    # INVESTMENTS
    # =========================
    "stocks": {

        "engine":
            stocks_score,

        "category":
            "investing",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.1,

        "label":
            "Stocks",

        "description":
            "Stock market scoring",
    },

    "etf": {

        "engine":
            etf_score,

        "category":
            "investing",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.1,

        "label":
            "ETF",

        "description":
            "ETF portfolio scoring",
    },

    "commodities": {

        "engine":
            commodities_score,

        "category":
            "investing",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            0.8,

        "label":
            "Commodities",

        "description":
            "Gold, silver, oil & commodities",
    },

    # =========================
    # ADVANCED MODULES
    # =========================
    "startup": {

        "engine":
            startup_score,

        "category":
            "venture",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            0.8,

        "label":
            "Startup",

        "description":
            "Startup investment scoring",
    },

    "private_equity": {

        "engine":
            private_equity_score,

        "category":
            "venture",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.4,

        "label":
            "Private Equity",

        "description":
            "Private equity scoring",
    },

    "franchise": {

        "engine":
            franchise_score,

        "category":
            "business",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            0.9,

        "label":
            "Franchise",

        "description":
            "Franchise business scoring",
    },

    "entrepreneurship": {

        "engine":
            entrepreneurship_score,

        "category":
            "business",

        "premium":
            False,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.2,

        "label":
            "Entrepreneurship",

        "description":
            "Entrepreneurial potential scoring",
    },

    "crowdfunding": {

        "engine":
            crowdfunding_score,

        "category":
            "alternative",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            0.6,

        "label":
            "Crowdfunding",

        "description":
            "Crowdfunding scoring",
    },

    "ai_business": {

        "engine":
            ai_business_score,

        "category":
            "ai",

        "premium":
            True,

        "active":
            True,

        "version":
            "v2",

        "weight":
            1.0,

        "label":
            "AI Business",

        "description":
            "AI business scoring",
    },
}


# =========================
# HELPERS
# =========================
def get_scoring_engine(
    module_name: str
):

    module = SCORING_ENGINES.get(module_name)

    if not module:
        return None

    if not module.get("active"):
        return None

    return module


def get_all_modules():

    return list(
        SCORING_ENGINES.keys()
    )


def get_premium_modules():

    return [

        name

        for name, module
        in SCORING_ENGINES.items()

        if module.get("premium")
    ]
