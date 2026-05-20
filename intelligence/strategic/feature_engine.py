
import logging

from product.entitlements import is_feature_enabled as entitlement_feature_enabled
from product.tiers import normalize_plan, unlocked_features_for_plan

logger = logging.getLogger(__name__)


def is_feature_enabled(user_plan: str, feature_key: str) -> bool:
    enabled = entitlement_feature_enabled(user_plan, feature_key)
    logger.info(
        "strategic_feature_check plan=%s feature=%s enabled=%s",
        normalize_plan(user_plan),
        feature_key,
        enabled,
    )
    return enabled

def compute_feature_access(profile: dict, score_data: dict, usage: dict = None):
    """
    Détermine les features accessibles selon :
    - plan utilisateur
    - score financier
    - richesse (assets)
    - engagement utilisateur
    """

    # =========================
    # SAFE INPUTS
    # =========================
    if not isinstance(profile, dict):
        profile = {}

    if not isinstance(score_data, dict):
        score_data = {}

    if not isinstance(usage, dict):
        usage = {}

    plan = normalize_plan(profile.get("plan"))
    # =========================
    # FEATURES SET (NO DUPLICATES)
    # =========================
    features = set()

    # =========================
    # 1. PLAN-BASED FEATURES
    # =========================
    features.update(unlocked_features_for_plan(plan))

    # =========================
    # 2. CLEAN OUTPUT
    # =========================
    return sorted(list(features))
