from .scrappers.bpi import search_bpi
from .scrappers.google_trends import get_trends
from .scrappers.financement import get_financements
from .scrappers.transmission import search_business_for_sale

from .analyzers.ai_analysis import analyze_business_ai
from .analyzers.opportunity_scoring import score_opportunity


def get_business_intelligence(query):

    results = []

    mode = query.mode.lower()  # ✅ sécurisation

    # 🔹 CREATE
    if mode == "create":

        ideas = search_bpi(query.sector)
        trends = get_trends(query.sector)

        for idea in ideas:

            score = score_opportunity(idea, mode)
            ai = analyze_business_ai(idea, mode)

            results.append({
                "type": "creation",
                "title": idea.get("title"),
                "score": score,
                "ai": ai,
                "trend": trends
            })

    # 🔹 GROW
    elif mode == "grow":

        financements = get_financements()

        for f in financements:

            score = score_opportunity(f, mode)
            ai = analyze_business_ai(f, mode)

            results.append({
                "type": "financement",
                "name": f.get("name"),
                "organisme": f.get("organisme"),
                "score": score,
                "ai": ai
            })

    # 🔹 BUY
    elif mode == "buy":

        businesses = search_business_for_sale(query.sector)

        for b in businesses:

            if b.get("price", 0) > query.budget:
                continue

            score = score_opportunity(b, mode)
            ai = analyze_business_ai(b, mode)

            results.append({
                "type": "acquisition",
                "title": b.get("title"),
                "price": b.get("price"),
                "score": score,
                "ai": ai
            })

    return results


def generate_business_ideas(sector, budget):
    ideas = []

    if sector == "informatique":
        ideas.append({
            "idea": "Agence marketing digital",
            "budget_required": 5000,
            "roi": "high"
        })

    if budget > 20000:
        ideas.append({
            "idea": "SaaS niche",
            "budget_required": 20000,
            "roi": "very high"
        })

    return ideas
