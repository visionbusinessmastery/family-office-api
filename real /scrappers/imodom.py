import requests
import os
from .analyzers.yield import calculate_yield
from .analyzers.scoring import score_property

def search_imodom(city: str):

    return [{
        "title": f"Annonce Imodom {city}",
        "price": 150000,
        "surface": 65,
        "source": "imodom"
    }]
