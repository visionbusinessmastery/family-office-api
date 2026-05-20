# =========================
# MODULE ENGINE
# =========================

import logging

from intelligence.scoring.module_registry import MODULES
from intelligence.strategic.feature_engine import is_feature_enabled
from product.tiers import normalize_plan

logger = logging.getLogger(__name__)

MODULE_FEATURES = {
    "real_estate": "real_estate_discovery",
    "stocks": "opportunity_discovery",
    "etf": "opportunity_discovery",
    "crypto": "opportunity_discovery",
    "commodities": "opportunity_discovery",
    "business": "business_discovery",
    "startup": "business_discovery",
    "franchise": "business_discovery",
    "private_equity": "business_discovery",
    "crowdfunding": "business_discovery",
    "wealth": "legacy_discovery",
}


# =========================
# GET ALL OPPORTUNITIES
# =========================
def get_all_opportunities(user_profile):

    all_opportunities = []
    plan = normalize_plan((user_profile or {}).get("plan"))

    for module_name, engine in MODULES.items():
        feature = MODULE_FEATURES.get(module_name, "opportunity_discovery")
        enabled = is_feature_enabled(plan, feature)
        logger.info(
            "module_access_event module=%s feature=%s plan=%s enabled=%s",
            module_name,
            feature,
            plan,
            enabled,
        )
        if not enabled:
            continue

        try:

            results = engine(user_profile)

            if results:
                all_opportunities.extend(results)

        except Exception as e:
            logger.warning("Module error %s: %s", module_name, e)

    return all_opportunities
