from pytrends.request import TrendReq


def get_trends(keyword):
    try:
        pytrends = TrendReq()
        pytrends.build_payload([keyword])

        data = pytrends.interest_over_time()

        if data.empty:
            return 0

        return int(data[keyword].mean())
    except Exception:
        # fallback neutre en cas d'échec API
        return 50
