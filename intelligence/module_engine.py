# =========================
# INTELLIGENCE MODULE ENGINE
# =========================
from intelligence.module_registry import MODULES


def get_all_opportunities(user_profile):

    results = {}

    for module_name, engine in MODULES.items():

        try:

            results[module_name] = engine(user_profile)

        except Exception as e:

            results[module_name] = {
                "error": str(e)
            }

    return results
