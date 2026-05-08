from data_engine.news_service import get_market_news, get_google_news


def get_news(query: str):

    news = get_market_news(query)
    news += get_google_news(query)

    return news[:10]
