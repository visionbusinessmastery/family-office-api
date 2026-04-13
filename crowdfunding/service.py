from .scrappers.wiseed import search_wiseed
from .scrappers.pretup import search_pretup
from .scrappers.bricks import search_bricks
from .scrappers.fundora import search_fundora

from .analyzers.yield_calc import calculate_yield
from .analyzers.scoring import score_project
from .analyzers.ai_analysis import analyze_project_ai


def get_crowdfunding_intelligence(query):

    projects = []

    projects += search_wiseed()
    projects += search_pretup()
    projects += search_bricks()
    projects += search_fundora()

    results = []

    for project in projects:

        yield_value = calculate_yield(project)
        score = score_project(project, query.risk_level)
        ai = analyze_project_ai(project)

        results.append({
            "name": project["name"],
            "return": yield_value,
            "risk": project["risk"],
            "duration": project["duration"],
            "score": score,
            "ai_analysis": ai,
            "source": project["source"]
        })

    return sorted(results, key=lambda x: x["score"], reverse=True)
