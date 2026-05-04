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


def get_market_news_mentions(tickers: list[str], days: int = 7) -> dict[str, int]:
    """시장 일반 뉴스에서 각 ticker가 몇 번 언급됐는지 카운팅"""
    client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    news = client.general_news("general", min_id=0)

    counts = {ticker: 0 for ticker in tickers}
    for article in news:
        text = (article.get("headline", "") + " " + article.get("summary", "")).upper()
        for ticker in tickers:
            if ticker in text:
                counts[ticker] += 1

    return counts
