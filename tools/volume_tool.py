import requests
from config import MAX_MARKET_CAP, MIN_MARKET_CAP, CANDIDATE_POOL

SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_most_active_by_dollar_volume(count: int = 20) -> list[str]:
    """
    Yahoo most_actives 스크리너에서 후보를 받아 시총 구간으로 거른 뒤
    거래대금(3개월 평균 거래량 × 현재가)으로 재정렬합니다.

    most_actives 는 '거래 주식 수' 기준이라 저가주에 편향됩니다.
    후보를 넓게(기본 250개, Yahoo 최대치) 받아야 고가주가 후보에서
    구조적으로 배제되지 않습니다.
    """
    res = requests.get(
        SCREENER_URL,
        params={"scrIds": "most_actives", "count": CANDIDATE_POOL},
        headers=HEADERS, timeout=15,
    )
    res.raise_for_status()
    quotes = res.json()["finance"]["result"][0]["quotes"]

    dollar_volumes = {}
    too_big = too_small = no_data = 0

    for q in quotes:
        ticker = q.get("symbol")
        market_cap = q.get("marketCap") or 0
        volume = q.get("averageDailyVolume3Month") or 0
        price = q.get("regularMarketPrice") or 0

        if not ticker or not market_cap or not volume or not price:
            no_data += 1
            continue
        if market_cap > MAX_MARKET_CAP:
            too_big += 1
            continue
        if market_cap < MIN_MARKET_CAP:
            too_small += 1
            continue

        dollar_volumes[ticker] = volume * price

    print(
        f"  [Volume] 후보 {len(quotes)}개 → 시총 필터 통과 {len(dollar_volumes)}개 "
        f"(상한 초과 {too_big} / 하한 미달 {too_small} / 데이터 없음 {no_data})"
    )

    ranked = sorted(dollar_volumes, key=dollar_volumes.get, reverse=True)[:count]

    print(f"  [Volume] 거래대금 상위 {len(ranked)}종목:")
    for i, ticker in enumerate(ranked[:5], 1):
        print(f"    {i}. {ticker}: ${dollar_volumes[ticker]/1e9:.1f}B/일")

    return ranked
