import os
from functools import lru_cache

from openai import OpenAI


@lru_cache(maxsize=1)
def get_ethan_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def is_ethan_openai_configured() -> bool:
    return get_ethan_openai_client() is not None


def ethan_chat_completion(**kwargs):
    client = get_ethan_openai_client()
    if not client:
        raise RuntimeError("OPENAI_API_KEY non configuree")
    return client.chat.completions.create(**kwargs)
