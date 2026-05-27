import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from product.tiers import PLAN_ORDER, plan_allows

PRICE_ENVS = {
    "gold": ["STRIPE_PRICE_GOLD_MONTHLY", "STRIPE_PRICE_GOLD_YEARLY"],
    "elite": ["STRIPE_PRICE_ELITE_MONTHLY", "STRIPE_PRICE_ELITE_YEARLY"],
    "liberty": ["STRIPE_PRICE_LIBERTY_MONTHLY", "STRIPE_PRICE_LIBERTY_YEARLY"],
    "legacy": ["STRIPE_PRICE_LEGACY_MONTHLY", "STRIPE_PRICE_LEGACY_YEARLY"],
}

FOUNDER_PRICE_ENVS = {
    "gold": ["STRIPE_PRICE_FOUNDER_GOLD_MONTHLY", "STRIPE_PRICE_FOUNDER_GOLD_YEARLY"],
    "elite": ["STRIPE_PRICE_FOUNDER_ELITE_MONTHLY", "STRIPE_PRICE_FOUNDER_ELITE_YEARLY"],
    "liberty": ["STRIPE_PRICE_FOUNDER_LIBERTY_MONTHLY", "STRIPE_PRICE_FOUNDER_LIBERTY_YEARLY"],
    "legacy": ["STRIPE_PRICE_FOUNDER_LEGACY_MONTHLY", "STRIPE_PRICE_FOUNDER_LEGACY_YEARLY"],
}


def main():
    failures = []
    warnings = []

    if os.getenv("STRIPE_MODE", "sandbox").lower() == "production":
        for key in ["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"]:
            if not os.getenv(key):
                failures.append(f"{key} manquant")

    for price_envs in PRICE_ENVS.values():
        for price_env in price_envs:
            if not os.getenv(price_env):
                warnings.append(f"{price_env} non configure")

    for price_envs in FOUNDER_PRICE_ENVS.values():
        for price_env in price_envs:
            if not os.getenv(price_env):
                warnings.append(f"{price_env} non configure")

    expected = ["FREE", "GOLD", "ELITE", "LIBERTY", "LEGACY"]
    if list(PLAN_ORDER.keys()) != expected:
        failures.append(f"Hierarchie plans inattendue: {PLAN_ORDER}")

    for upper_plan in expected:
        for lower_plan in expected:
            if PLAN_ORDER[upper_plan] >= PLAN_ORDER[lower_plan] and not plan_allows(upper_plan, lower_plan):
                failures.append(f"Heritage casse: {upper_plan} doit inclure {lower_plan}")

    if os.getenv("STRIPE_FOUNDER_COUPON_ID"):
        print("Founder coupon: configured")
    else:
        warnings.append("STRIPE_FOUNDER_COUPON_ID non configure")

    print("WHITE ROCK Stripe production check")
    print("Failures:", failures or "none")
    print("Warnings:", warnings or "none")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
