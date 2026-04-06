import requests
import os
from config import FMP_API_KEY
from openai import OpenAI

FMP_API_KEY = os.getenv("FMP_API_KEY")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
