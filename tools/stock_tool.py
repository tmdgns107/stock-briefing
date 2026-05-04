import yfinance as yf


def format_market_cap(value: float | None) -> str:
    if not value:
        return "N/A"
    if value >= 1_000_000_000_000:
        t = value / 1_000_000_000_000
        return f"{t:.1f}조 달러({t:.1f}T)"
    if value >= 100_000_000_000:
        b = value / 1_000_000_000
        억 = value / 100_000_000
        return f"{억:.0f}억 달러({b:.0f}B)"
    if value >= 1_000_000_000:
        b = value / 1_000_000_000
        억 = value / 100_000_000
        return f"{억:.0f}억 달러({b:.1f}B)"
    m = value / 1_000_000
    return f"{m:.0f}백만 달러({m:.0f}M)"


def get_stock_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    hist = stock.history(period="6d")

    if hist.empty or len(hist) < 2:
        return {"error": f"{ticker} 데이터를 가져올 수 없습니다."}

    prev_close = hist["Close"].iloc[0]
    curr_close = hist["Close"].iloc[-1]
    weekly_change_pct = ((curr_close - prev_close) / prev_close) * 100

    info = stock.info

    return {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "price": round(curr_close, 2),
        "weekly_change_pct": round(weekly_change_pct, 2),
        "market_cap_raw": info.get("marketCap"),
        "market_cap": format_market_cap(info.get("marketCap")),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "eps": info.get("trailingEps"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "target_price": info.get("targetMeanPrice"),
    }
