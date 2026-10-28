import requests
from config import (
    MAX_MARKET_CAP, MIN_MARKET_CAP, CANDIDATE_POOL, MIN_DOLLAR_VOLUME,
)

SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_most_active_by_dollar_volume(
    count: int = 20,
) -> tuple[list[str], dict[str, float], dict[str, float]]:
    """
    (신호 측정 대상 티커, 필터 통과 전체의 거래대금, 전체의 현재가) 를 반환합니다.

    거래대금 dict 가 'count 개'가 아니라 '필터를 통과한 전체'인 이유:
    거래대금 점수를 상위 count 개 안에서 정규화하면, 그 집단은 이미 거래대금이
    서로 비슷하므로 min-max 가 미세한 차이를 0~100 으로 증폭합니다. 1위와
    count 위의 실제 차이가 1.1 배든 3 배든 점수는 항상 100 대 0 이 됩니다.
    전체 모집단을 기준으로 정규화해야 '상위권은 다 비슷하다'가 점수로 표현되고,
    남은 변별력이 펀더멘털·버즈로 넘어갑니다.

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
    prices = {}
    too_big = too_small = illiquid = no_data = 0

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

        dollar_volume = volume * price
        # 순위가 아닌 절대 기준으로 유동성을 거른다. 순위로만 자르면 그 주
        # 전체 거래가 한산해도 상위 count 개는 늘 통과한다.
        if dollar_volume < MIN_DOLLAR_VOLUME:
            illiquid += 1
            continue

        dollar_volumes[ticker] = dollar_volume
        prices[ticker] = price

    print(
        f"  [Volume] 후보 {len(quotes)}개 → 통과 {len(dollar_volumes)}개 "
        f"(시총 상한 {too_big} / 하한 {too_small} / 유동성 미달 {illiquid} / 데이터 없음 {no_data})"
    )

    ranked = sorted(dollar_volumes, key=dollar_volumes.get, reverse=True)[:count]

    print(f"  [Volume] 거래대금 상위 {len(ranked)}종목:")
    for i, ticker in enumerate(ranked[:5], 1):
        print(f"    {i}. {ticker}: ${dollar_volumes[ticker]/1e9:.1f}B/일")

    return ranked, dollar_volumes, prices
