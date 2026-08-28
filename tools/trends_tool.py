import os
import time
import finnhub

BASELINE_WEEKS = 4      # 기준선으로 삼을 직전 주 수
MIN_BASELINE = 3.0      # 분모 하한 — 평소 뉴스가 거의 없는 종목의 배수 폭주 방지
RATIO_CAP = 5.0         # 배수 상한 — 이상치가 정규화를 독점하지 않도록
API_INTERVAL = 0.8       # Finnhub 무료 티어 60 calls/min 준수 (요청 시간 포함 ~1.1s/call)

_WEEK = 7 * 86400


def _day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def get_news_buzz_scores(tickers: list[str]) -> dict[str, float]:
    """
    '이번 주 뉴스량 ÷ 직전 N주 평균 주간 뉴스량' 배수를 반환합니다.

    절대 건수를 쓰면 뉴스가 원래 많은 대형주가 항상 이깁니다(= 인지도 측정).
    주간 브리핑의 목적은 '이번 주 주목받은' 종목을 찾는 것이므로
    평소 대비 뉴스가 얼마나 튀었는지를 봅니다.

    주의: Finnhub company_news 는 한 번에 반환하는 건수에 상한(~250건)이 있어
    35일을 한 번에 조회하면 과거 주가 잘립니다(CRM 실측: 통합 조회 시
    [135,24,71,9,0] → 주 단위 조회 시 [135,42,81,93,111]). 반드시 주 단위로
    조회합니다. 단, 한 주에 250건을 넘는 종목은 그 주도 잘리므로 배수가
    실제보다 낮게 나올 수 있습니다.
    """
    client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    now = time.time()
    scores = {}

    for ticker in tickers:
        weekly = []
        try:
            for w in range(BASELINE_WEEKS + 1):
                end = now - w * _WEEK
                news = client.company_news(
                    ticker, _from=_day(end - _WEEK), to=_day(end)
                )
                weekly.append(len(news))
                time.sleep(API_INTERVAL)
        except Exception as e:
            print(f"  [Buzz] {ticker} 오류: {type(e).__name__}: {e}")
            scores[ticker] = 0.0
            continue

        this_week = weekly[0]
        baseline = sum(weekly[1:]) / BASELINE_WEEKS if len(weekly) > 1 else 0.0
        ratio = min(this_week / max(baseline, MIN_BASELINE), RATIO_CAP)
        scores[ticker] = round(ratio, 2)

        print(
            f"  [Buzz] {ticker}: {ratio:.2f}배 "
            f"(이번주 {this_week}건 / 평소 {baseline:.1f}건) {weekly}"
        )

    return scores
