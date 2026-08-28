import os
import time
import finnhub


def get_news(ticker: str, days: int = 7) -> list[dict]:
    client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])

    end = int(time.time())
    start = end - (days * 24 * 60 * 60)

    news = client.company_news(
        ticker,
        _from=time.strftime("%Y-%m-%d", time.localtime(start)),
        to=time.strftime("%Y-%m-%d", time.localtime(end)),
    )

    return [
        {"headline": n["headline"], "summary": n.get("summary", ""), "source": n["source"]}
        for n in news[:5]
    ]
