from tools.volume_tool import get_most_active_by_dollar_volume
from tools.news_tool import get_market_news_mentions
from tools.trends_tool import get_news_buzz_scores
from tools.fundamental_tool import get_fundamental_scores
from config import TOP_N


def discovery_node(state: dict) -> dict:
    print("[ Discovery Node ] 거래금액 상위 종목 수집 중...")
    active_tickers = get_most_active_by_dollar_volume(count=20)

    print("\n[ Discovery Node ] 펀더멘털 점수 수집 중...")
    fundamental_scores = get_fundamental_scores(active_tickers)

    print("\n[ Discovery Node ] 뉴스 버즈 수집 중...")
    buzz_scores = get_news_buzz_scores(active_tickers)

    print("\n[ Discovery Node ] 시장 뉴스 언급 빈도 수집 중...")
    mention_scores = get_market_news_mentions(active_tickers)

    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    def normalize(scores: dict) -> dict:
        max_val = max(scores.values()) if scores and max(scores.values()) > 0 else 1
        return {k: v / max_val * 100 for k, v in scores.items()}

    vol_norm = normalize(volume_scores)
    fund_norm = fundamental_scores
    buzz_norm = normalize(buzz_scores)
    mention_norm = normalize(mention_scores)

    combined = {
        ticker: (
            vol_norm.get(ticker, 0) * 0.4
            + fund_norm.get(ticker, 50) * 0.3
            + buzz_norm.get(ticker, 0) * 0.2
            + mention_norm.get(ticker, 0) * 0.1
        )
        for ticker in active_tickers
    }

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

    print(f"\n[ Discovery Node ] 선정 완료: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        s = scores[ticker]
        print(f"  {ticker}: 종합 {s['total']} (거래금액 {s['volume']:.0f} / 펀더멘털 {s['fundamental']:.0f} / 버즈 {s['buzz']:.0f} / 언급 {s['mention']:.0f})")

    return {"tickers": top_tickers, "scores": scores}
