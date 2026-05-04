from tools.volume_tool import get_most_active_by_dollar_volume
from tools.news_tool import get_market_news_mentions
from tools.trends_tool import get_news_buzz_scores
from tools.fundamental_tool import get_fundamental_scores
from config import TOP_N


def discover_tickers() -> tuple[list[str], dict]:
    """
    4가지 신호를 종합해 이번 주 주목할 종목 TOP N을 반환합니다.

    신호별 가중치:
      - 거래금액    : 40%  (실제 자금 이동량)
      - 펀더멘털    : 30%  (PEG 40% + ROE 30% + EPS 성장률 30%)
      - 뉴스 버즈   : 20%  (Finnhub 종목별 뉴스 건수)
      - 시장 언급   : 10%  (일반 시장 뉴스 언급 횟수)
    """
    print("[ 1/4 ] 거래금액 상위 종목 수집 중...")
    active_tickers = get_most_active_by_dollar_volume(count=20)

    print("\n[ 2/4 ] 펀더멘털 점수 수집 중...")
    fundamental_scores = get_fundamental_scores(active_tickers)

    print("\n[ 3/4 ] 종목별 뉴스 버즈 수집 중...")
    buzz_scores = get_news_buzz_scores(active_tickers)

    print("\n[ 4/4 ] 시장 뉴스 언급 빈도 수집 중...")
    mention_scores = get_market_news_mentions(active_tickers)

    # 거래금액: 순위 기반 점수 (1위=20점 → 정규화)
    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    def normalize(scores: dict) -> dict:
        max_val = max(scores.values()) if scores and max(scores.values()) > 0 else 1
        return {k: v / max_val * 100 for k, v in scores.items()}

    vol_norm = normalize(volume_scores)
    fund_norm = fundamental_scores  # 이미 0~100 범위
    buzz_norm = normalize(buzz_scores)
    mention_norm = normalize(mention_scores)

    combined = {}
    for ticker in active_tickers:
        combined[ticker] = (
            vol_norm.get(ticker, 0) * 0.4
            + fund_norm.get(ticker, 50) * 0.3
            + buzz_norm.get(ticker, 0) * 0.2
            + mention_norm.get(ticker, 0) * 0.1
        )

    top_tickers = sorted(combined, key=combined.get, reverse=True)[:TOP_N]

    scores = {
        ticker: {
            "total": round(combined[ticker], 1),
            "volume": round(vol_norm.get(ticker, 0), 1),
            "fundamental": round(fund_norm.get(ticker, 50), 1),
            "buzz": round(buzz_norm.get(ticker, 0), 1),
            "mention": round(mention_norm.get(ticker, 0), 1),
        }
        for ticker in top_tickers
    }

    print(f"\n이번 주 선정 종목: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        s = scores[ticker]
        print(
            f"  {ticker}: 종합 {s['total']} "
            f"(거래금액 {s['volume']:.0f} / 펀더멘털 {s['fundamental']:.0f} / "
            f"버즈 {s['buzz']:.0f} / 언급 {s['mention']:.0f})"
        )

    return top_tickers, scores
