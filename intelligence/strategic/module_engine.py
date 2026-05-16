# =========================
# MODULE ENGINE
# =========================

from intelligence.scoring.module_registry import MODULES


# =========================
# GET ALL OPPORTUNITIES
# =========================
def get_all_opportunities(user_profile):

    all_opportunities = []

    for module_name, engine in MODULES.items():

        try:

            results = engine(user_profile)

            if results:
                all_opportunities.extend(results)

        except Exception as e:

            print(f"MODULE ERROR {module_name}: {e}")

    return all_opportunities
