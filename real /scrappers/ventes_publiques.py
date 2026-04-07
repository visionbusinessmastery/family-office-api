import requests
import os
from .analyzers.yield import calculate_yield
from .analyzers.scoring import score_property

def search_ventes_publiques(city: str):

    return [{
        "title": f"Bien saisi {city}",
        "price": 90000,
        "surface": 80,
        "source": "ventes_publiques"
    }]
