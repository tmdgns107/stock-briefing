import time
from pytrends.request import TrendReq


def get_trends_scores(tickers: list[str]) -> dict[str, int]:
    """ticker 리스트의 Google Trends 점수를 반환 (0~100)"""
    pytrends = TrendReq(hl="en-US", tz=360)
    scores = {}

    # pytrends는 한 번에 최대 5개 비교 가능
    for i in range(0, len(tickers), 5):
        batch = tickers[i:i + 5]
        try:
            pytrends.build_payload(batch, timeframe="now 7-d", geo="US")
            data = pytrends.interest_over_time()
            if not data.empty:
                for ticker in batch:
                    if ticker in data.columns:
                        scores[ticker] = int(data[ticker].mean())
                    else:
                        scores[ticker] = 0
        except Exception:
            for ticker in batch:
                scores[ticker] = 0
        time.sleep(1)  # rate limit 방지

    return scores
