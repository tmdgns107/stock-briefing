import requests
import yfinance as yf


def get_most_active_by_dollar_volume(count: int = 20) -> list[str]:
    """
    거래량 상위 30종목을 가져온 뒤 거래금액(volume × price)으로 재정렬합니다.
    주식 수 기준 거래량은 저가주에 왜곡되므로 실제 돈의 이동량으로 측정합니다.
    """
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {"scrIds": "most_actives", "count": 30}
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, params=params, headers=headers, timeout=10)
    res.raise_for_status()

    quotes = res.json()["finance"]["result"][0]["quotes"]
    candidates = [q["symbol"] for q in quotes]

    # 거래금액(dollar volume) 계산: volume × price
    dollar_volumes = {}
    tickers = yf.Tickers(" ".join(candidates))
    for ticker in candidates:
        try:
            info = tickers.tickers[ticker].fast_info
            volume = getattr(info, "three_month_average_volume", 0) or 0
            price = getattr(info, "last_price", 0) or 0
            dollar_volumes[ticker] = volume * price
        except Exception:
            dollar_volumes[ticker] = 0

    ranked = sorted(dollar_volumes, key=dollar_volumes.get, reverse=True)[:count]

    print(f"  [Volume] 거래금액 상위 {count}종목:")
    for i, ticker in enumerate(ranked[:5], 1):
        dv = dollar_volumes[ticker]
        print(f"    {i}. {ticker}: ${dv/1e9:.1f}B/일")

    return ranked
