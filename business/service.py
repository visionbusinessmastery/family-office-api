from .scrappers.bpi import search_bpi
from .scrappers.google_trends import get_trends
from .scrappers.financement import get_financements
from .scrappers.transmission import search_business_for_sale

from .analyzers.ai_analysis import analyze_business_ai
from .analyzers.opportunity_scoring import score_opportunity


def get_business_intelligence(query):

    results = []

    # 🔹 CREATE
    if query.mode == "create":

        ideas = search_bpi(query.sector)
        trends = get_trends(query.sector)

        for idea in ideas:

            score = score_opportunity(idea, query.mode)
            ai = analyze_business_ai(idea, query.mode)

            results.append({
                "type": "creation",
                "title": idea["title"],
                "score": score,
                "ai": ai,
                "trend": trends
            })

    # 🔹 GROW
    elif query.mode == "grow":

        financements = get_financements()

        for f in financements:

            score = score_opportunity(f, query.mode)
            ai = analyze_business_ai(f, query.mode)

            results.append({
                "type": "financement",
                "name": f["name"],
                "organisme": f["organisme"],
                "score": score,
                "ai": ai
            })

    # 🔹 BUY
    elif query.mode == "buy":

        businesses = search_business_for_sale(query.sector)

        for b in businesses:

            if b["price"] > query.budget:
                continue

            score = score_opportunity(b, query.mode)
            ai = analyze_business_ai(b, query.mode)

            results.append({
                "type": "acquisition",
                "title": b["title"],
                "price": b["price"],
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
