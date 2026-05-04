import os
import time
import finnhub


def get_news_buzz_scores(tickers: list[str], days: int = 7) -> dict[str, int]:
    """
    Finnhub 종목별 뉴스 건수를 트렌드 대용 신호로 반환합니다.
    뉴스가 많을수록 시장 관심도가 높다고 판단합니다.
    """
    client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])

    end = time.strftime("%Y-%m-%d")
    start = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))

    scores = {}
    for ticker in tickers:
        try:
            news = client.company_news(ticker, _from=start, to=end)
            scores[ticker] = len(news)
            print(f"  [Buzz] {ticker}: 뉴스 {len(news)}건")
        except Exception as e:
            print(f"  [Buzz] {ticker} 오류: {e}")
            scores[ticker] = 0
        time.sleep(0.3)

    return scores
