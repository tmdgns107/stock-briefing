from tools.volume_tool import get_most_active
from tools.news_tool import get_market_news_mentions
from tools.trends_tool import get_trends_scores
from config import TOP_N


def discover_tickers() -> tuple[list[str], dict]:
    """
    3가지 신호를 종합해 이번 주 주목할 종목 TOP N을 반환합니다.

    Returns:
        tickers: 선정된 종목 리스트
        scores: 종목별 신호 점수 dict
    """
    print("[ 1/3 ] 거래량 상위 종목 수집 중...")
    active_tickers = get_most_active(count=20)

    print("[ 2/3 ] Google Trends 점수 수집 중...")
    trends_scores = get_trends_scores(active_tickers)

    print("[ 3/3 ] 뉴스 언급 빈도 수집 중...")
    news_mentions = get_market_news_mentions(active_tickers)

    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    def normalize(scores: dict) -> dict:
        max_val = max(scores.values()) if scores and max(scores.values()) > 0 else 1
        return {k: v / max_val * 100 for k, v in scores.items()}

    vol_norm = normalize(volume_scores)
    trends_norm = normalize(trends_scores)
    news_norm = normalize(news_mentions)

    combined = {}
    for ticker in active_tickers:
        combined[ticker] = (
            vol_norm.get(ticker, 0) * 0.5
            + trends_norm.get(ticker, 0) * 0.3
            + news_norm.get(ticker, 0) * 0.2
        )

    top_tickers = sorted(combined, key=combined.get, reverse=True)[:TOP_N]

    scores = {
        ticker: {
            "total": round(combined[ticker], 1),
            "volume": round(vol_norm.get(ticker, 0), 1),
            "trends": round(trends_norm.get(ticker, 0), 1),
            "news": round(news_norm.get(ticker, 0), 1),
        }
        for ticker in top_tickers
    }

    print(f"\n이번 주 선정 종목: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        s = scores[ticker]
        print(f"  {ticker}: 종합 {s['total']} (거래량 {s['volume']} / 트렌드 {s['trends']} / 뉴스 {s['news']})")

    return top_tickers, scores
