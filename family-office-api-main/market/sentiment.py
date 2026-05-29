from core.openai_gateway import chat_completion, is_openai_configured

def analyze_sentiment(news_list):
    if not is_openai_configured():
        return {
            "label": "neutral",
            "score": 50,
            "summary": "OPENAI_API_KEY non configuree"
        }

    text = ""

    for article in news_list:
        text += article.get("title", "") + "\n"

    prompt = f"""
    Analyse le sentiment global de ces news financières:

    {text}

    Donne:
    - sentiment global (bullish / bearish / neutre)
    - score sur 100
    - résumé en 3 lignes
    """

    response = chat_completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
