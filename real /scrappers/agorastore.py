import requests
import os
from .analyzers.yield import calculate_yield
from .analyzers.scoring import score_property

def search_agorastore(city: str):

    return [{
        "title": f"Enchère publique {city}",
        "price": 70000,
        "surface": 75,
        "source": "agorastore"
    }]
