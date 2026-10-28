import time

from tools import finnhub_client
from tools.news_sentiment import negative_share

BASELINE_WEEKS = 4      # 기준선으로 삼을 직전 주 수
MIN_BASELINE = 3.0      # 분모 하한 — 평소 뉴스가 거의 없는 종목의 배수 폭주 방지
RATIO_CAP = 5.0         # 배수 상한 — 이상치가 정규화를 독점하지 않도록

_WEEK = 7 * 86400


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def get_news_buzz_scores(tickers: list[str]) -> dict[str, dict]:
    """
    종목별 {"ratio", "negative_share", "neg", "pos"} 를 반환합니다.

    ratio = 이번 주 뉴스량 ÷ 직전 N주 평균 주간 뉴스량
    절대 건수를 쓰면 뉴스가 원래 많은 대형주가 항상 이깁니다(= 인지도 측정).
    주간 브리핑의 목적은 '이번 주 주목받은' 종목을 찾는 것이므로
    평소 대비 뉴스가 얼마나 튀었는지를 봅니다.

    negative_share 는 이번 주 헤드라인의 악재 비중입니다. 뉴스가 늘어난
    '이유'를 보지 않으면 소송·리콜로 폭증한 종목이 추천 상위에 올라옵니다.
    이번 주 응답을 그대로 재사용하므로 추가 API 호출은 없습니다.

    주의: Finnhub company_news 는 한 번에 반환하는 건수에 상한(~250건)이 있어
    35일을 한 번에 조회하면 과거 주가 잘립니다(CRM 실측: 통합 조회 시
    [135,24,71,9,0] → 주 단위 조회 시 [135,42,81,93,111]). 반드시 주 단위로
    조회합니다. 단, 한 주에 250건을 넘는 종목은 그 주도 잘리므로 배수가
    실제보다 낮게 나올 수 있습니다.
    """
    now = time.time()
    results = {}

    for ticker in tickers:
        weekly = []
        this_week_news = []
        try:
            for w in range(BASELINE_WEEKS + 1):
                end = now - w * _WEEK
                news = finnhub_client.call(
                    "company_news", ticker, _from=_day(end - _WEEK), to=_day(end)
                )
                weekly.append(len(news))
                if w == 0:
                    this_week_news = news
        except Exception as e:
            print(f"  [Buzz] {ticker} 오류: {type(e).__name__}: {e}")
            # 조회 실패를 0.0 으로 두면 '뉴스가 안 늘었음'과 같은 취급이 되어
            # 정규화 최하점이 됩니다. 결측은 중립 배수(1.0)로 둡니다.
            results[ticker] = {
                "ratio": 1.0, "negative_share": 0.0, "neg": 0, "pos": 0, "missing": True,
            }
            continue

        this_week = weekly[0]
        baseline = sum(weekly[1:]) / BASELINE_WEEKS if len(weekly) > 1 else 0.0
        ratio = min(this_week / max(baseline, MIN_BASELINE), RATIO_CAP)
        neg_share, neg, pos = negative_share(this_week_news)

        results[ticker] = {
            "ratio": round(ratio, 2),
            "negative_share": round(neg_share, 2),
            "neg": neg,
            "pos": pos,
            "missing": False,
        }

        tone = f"악재 {neg}/호재 {pos}" if (neg or pos) else "방향 불명"
        print(
            f"  [Buzz] {ticker}: {ratio:.2f}배 "
            f"(이번주 {this_week}건 / 평소 {baseline:.1f}건) {weekly} | {tone}"
        )

    return results
