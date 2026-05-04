from tools.volume_tool import get_most_active
from tools.news_tool import get_market_news_mentions
from tools.trends_tool import get_trends_scores
from config import TOP_N


def discover_tickers() -> list[str]:
    """
    3가지 신호를 종합해 이번 주 주목할 종목 TOP N을 반환합니다.

    신호별 가중치:
      - 거래량 순위   : 50%  (시장 관심도의 가장 직접적인 지표)
      - Google Trends : 30%  (일반 투자자 검색 관심도)
      - 뉴스 언급 빈도 : 20%  (미디어 노출도)
    """
    print("[ 1/3 ] 거래량 상위 종목 수집 중...")
    active_tickers = get_most_active(count=20)

    print("[ 2/3 ] Google Trends 점수 수집 중...")
    trends_scores = get_trends_scores(active_tickers)

    print("[ 3/3 ] 뉴스 언급 빈도 수집 중...")
    news_mentions = get_market_news_mentions(active_tickers)

    # 거래량: 순위 기반 점수 (1위=20점, 2위=19점, ...)
    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    # 각 신호 정규화 후 가중 합산
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

    print(f"\n이번 주 선정 종목: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        print(
            f"  {ticker}: 종합점수 {combined[ticker]:.1f} "
            f"(거래량 {vol_norm.get(ticker, 0):.0f} / "
            f"트렌드 {trends_norm.get(ticker, 0):.0f} / "
            f"뉴스 {news_norm.get(ticker, 0):.0f})"
        )

    return top_tickers
