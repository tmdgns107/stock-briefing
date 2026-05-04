import yfinance as yf


def get_stock_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2d")

    if hist.empty or len(hist) < 2:
        return {"error": f"{ticker} 데이터를 가져올 수 없습니다."}

    prev_close = hist["Close"].iloc[-2]
    curr_close = hist["Close"].iloc[-1]
    change_pct = ((curr_close - prev_close) / prev_close) * 100

    info = stock.info

    return {
        "ticker": ticker,
        "name": info.get("longName", ticker),
        "price": round(curr_close, 2),
        "change_pct": round(change_pct, 2),
        "volume": info.get("volume", 0),
        "market_cap": info.get("marketCap", 0),
        "pe_ratio": info.get("trailingPE"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }
