from tools.volume_tool import get_most_active_by_dollar_volume
from tools.trends_tool import get_news_buzz_scores
from tools.fundamental_tool import get_fundamental_scores
from config import (
    TOP_N, WEIGHT_VOLUME, WEIGHT_FUNDAMENTAL, WEIGHT_BUZZ, MAX_PER_SECTOR,
)


def discovery_node(state: dict) -> dict:
    print("[ Discovery Node ] 거래대금 상위 종목 수집 중...")
    active_tickers = get_most_active_by_dollar_volume(count=20)

    print("\n[ Discovery Node ] 펀더멘털 점수 수집 중...")
    fundamental_scores, sectors = get_fundamental_scores(active_tickers)

    print("\n[ Discovery Node ] 뉴스 버즈 수집 중 (평소 대비 배수)...")
    buzz_scores = get_news_buzz_scores(active_tickers)

    volume_scores = {ticker: (20 - i) for i, ticker in enumerate(active_tickers)}

    def normalize(scores: dict) -> dict:
        max_val = max(scores.values()) if scores and max(scores.values()) > 0 else 1
        return {k: v / max_val * 100 for k, v in scores.items()}

    vol_norm = normalize(volume_scores)
    fund_norm = fundamental_scores
    buzz_norm = normalize(buzz_scores)

    combined = {
        ticker: (
            vol_norm.get(ticker, 0) * WEIGHT_VOLUME
            + fund_norm.get(ticker, 50) * WEIGHT_FUNDAMENTAL
            + buzz_norm.get(ticker, 0) * WEIGHT_BUZZ
        )
        for ticker in active_tickers
    }

    ranked = sorted(combined, key=combined.get, reverse=True)
    top_tickers = _pick_diversified(ranked, sectors)

    scores = {
        ticker: {
            "total": round(combined[ticker], 1),
            "volume": round(vol_norm.get(ticker, 0), 1),
            "fundamental": round(fund_norm.get(ticker, 50), 1),
            "buzz": round(buzz_norm.get(ticker, 0), 1),
        }
        for ticker in top_tickers
    }

    dist = {}
    for ticker in top_tickers:
        sec = sectors.get(ticker, "기타")
        dist[sec] = dist.get(sec, 0) + 1
    print(f"  섹터 분포: {' / '.join(f'{k} {v}' for k, v in dist.items())}")

    print(f"\n[ Discovery Node ] 선정 완료: {', '.join(top_tickers)}")
    for ticker in top_tickers:
        s = scores[ticker]
        print(
            f"  {ticker}: 종합 {s['total']} "
            f"(거래대금 {s['volume']:.0f} / 펀더멘털 {s['fundamental']:.0f} / 버즈 {s['buzz']:.0f})"
            f" [{sectors.get(ticker, '기타')}]"
        )

    return {"tickers": top_tickers, "scores": scores}


def _pick_diversified(ranked: list[str], sectors: dict[str, str]) -> list[str]:
    """
    점수 순으로 뽑되 한 섹터에서 MAX_PER_SECTOR 개까지만 담습니다.

    제약 없이 뽑으면 매주 테크/반도체로만 채워져 테마 분석까지
    같은 결론이 반복됩니다. 제약 때문에 TOP_N 을 못 채우면
    남은 자리는 점수 순으로 보충합니다.
    """
    picked, counts, skipped = [], {}, []

    for ticker in ranked:
        if len(picked) == TOP_N:
            break
        sector = sectors.get(ticker, "기타")
        if counts.get(sector, 0) >= MAX_PER_SECTOR:
            skipped.append(f"{ticker}({sector})")
            continue
        picked.append(ticker)
        counts[sector] = counts.get(sector, 0) + 1

    if skipped:
        print(f"  섹터 제한으로 제외: {', '.join(skipped)}")

    # 제약이 강해 자리가 남으면 점수 순으로 채움
    if len(picked) < TOP_N:
        for ticker in ranked:
            if ticker not in picked:
                picked.append(ticker)
                if len(picked) == TOP_N:
                    break
        print(f"  섹터 제약 완화로 보충 (최종 {len(picked)}종목)")

    return picked
