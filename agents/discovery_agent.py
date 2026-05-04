from tools.volume_tool import get_most_active
from tools.news_tool import get_market_news_mentions
from tools.trends_tool import get_news_buzz_scores
from config import TOP_N


def discover_tickers() -> tuple[list[str], dict]:
    """
    3가지 신호를 종합해 이번 주 주목할 종목 TOP N을 반환합니다.

    신호별 가중치:
      - 거래량 순위   : 50%
      - 종목 뉴스 버즈 : 30%  (Finnhub 종목별 뉴스 건수 — Google Trends 대체)
      - 시장 뉴스 언급 : 20%  (일반 시장 뉴스에서 티커 언급 횟수)
    """
    print("[ 1/3 ] 거래량 상위 종목 수집 중...")
    active_tickers = get_most_active(count=20)

    print("[ 2/3 ] 종목별 뉴스 버즈 수집 중...")
    buzz_scores = get_news_buzz_scores(active_tickers)

    print("[ 3/3 ] 시장 뉴스 언급 빈도 수집 중...")
    mention_scores = get_market_news_mentions(active_tickers)

    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    def normalize(scores: dict) -> dict:
        max_val = max(scores.values()) if scores and max(scores.values()) > 0 else 1
        return {k: v / max_val * 100 for k, v in scores.items()}

    vol_norm = normalize(volume_scores)
    buzz_norm = normalize(buzz_scores)
    mention_norm = normalize(mention_scores)

    combined = {}
    for ticker in active_tickers:
        combined[ticker] = (
            vol_norm.get(ticker, 0) * 0.5
            + buzz_norm.get(ticker, 0) * 0.3
            + mention_norm.get(ticker, 0) * 0.2
        )

    top_tickers = sorted(combined, key=combined.get, reverse=True)[:TOP_N]

    scores = {
        ticker: {
            "total": round(combined[ticker], 1),
            "volume": round(vol_norm.get(ticker, 0), 1),
            "buzz": round(buzz_norm.get(ticker, 0), 1),
            "mention": round(mention_norm.get(ticker, 0), 1),
        }
        for ticker in top_tickers
    }

    print(f"\n이번 주 선정 종목: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        s = scores[ticker]
        print(f"  {ticker}: 종합 {s['total']} (거래량 {s['volume']} / 버즈 {s['buzz']} / 언급 {s['mention']})")

    return top_tickers, scores
