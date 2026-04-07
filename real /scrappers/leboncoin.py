import requests
import os
from .analyzers.yield import calculate_yield
from .analyzers.scoring import score_property

def search_leboncoin(city: str):
    return [{
        "title": f"Annonce Leboncoin {city}",
        "price": 120000,
        "surface": 60,
        "source": "leboncoin"
    }]
