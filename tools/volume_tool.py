import requests
import yfinance as yf

MAX_MARKET_CAP = 500_000_000_000  # $500B


def get_most_active_by_dollar_volume(count: int = 20) -> list[str]:
    """
    거래량 상위 50종목을 가져온 뒤 시총 $500B 이하만 필터링 후
    거래금액(volume × price)으로 재정렬합니다.
    """
    url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    params = {"scrIds": "most_actives", "count": 50}
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, params=params, headers=headers, timeout=10)
    res.raise_for_status()

    quotes = res.json()["finance"]["result"][0]["quotes"]
    candidates = [q["symbol"] for q in quotes]

    dollar_volumes = {}
    filtered_out = []

    tickers = yf.Tickers(" ".join(candidates))
    for ticker in candidates:
        try:
            info = tickers.tickers[ticker].fast_info
            market_cap = getattr(info, "market_cap", 0) or 0

            if market_cap > MAX_MARKET_CAP:
                filtered_out.append(f"{ticker}(${market_cap/1e12:.1f}T)")
                continue

            volume = getattr(info, "three_month_average_volume", 0) or 0
            price = getattr(info, "last_price", 0) or 0
            dollar_volumes[ticker] = volume * price

        except Exception:
            dollar_volumes[ticker] = 0

    if filtered_out:
        print(f"  [Volume] 시총 $500B 초과 제외: {', '.join(filtered_out)}")

    ranked = sorted(dollar_volumes, key=dollar_volumes.get, reverse=True)[:count]

    print(f"  [Volume] 거래금액 상위 {len(ranked)}종목 (시총 $500B 이하):")
    for i, ticker in enumerate(ranked[:5], 1):
        dv = dollar_volumes[ticker]
        print(f"    {i}. {ticker}: ${dv/1e9:.1f}B/일")

    return ranked
