import yfinance as yf


def _clamp(value: float, min_val=0.0, max_val=100.0) -> float:
    return max(min_val, min(max_val, value))


def _peg_score(peg) -> float:
    """PEG < 1 = 이상적, 2 이상 = 고평가. None이면 50점(중립)."""
    if peg is None or peg <= 0:
        return 50.0
    if peg <= 1.0:
        return 100.0
    if peg <= 2.0:
        return _clamp(100 - (peg - 1.0) * 50)
    return _clamp(100 - (peg - 1.0) * 30)


def _roe_score(roe) -> float:
    """ROE 20% 이상 = 100점, 0% 이하 = 0점."""
    if roe is None:
        return 50.0
    pct = roe * 100
    return _clamp(pct * 5)


def _eps_growth_score(growth) -> float:
    """EPS 성장률 50% 이상 = 100점, 음수 = 0점."""
    if growth is None:
        return 50.0
    pct = growth * 100
    if pct <= 0:
        return 0.0
    return _clamp(pct * 2)


def get_fundamental_scores(tickers: list[str]) -> dict[str, float]:
    """
    PEG(40%) + ROE(30%) + EPS 성장률(30%) 가중 합산으로 펀더멘털 점수를 반환합니다.
    """
    scores = {}

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info

            peg = info.get("pegRatio")
            roe = info.get("returnOnEquity")
            eps_growth = info.get("earningsGrowth")

            score = (
                _peg_score(peg) * 0.4
                + _roe_score(roe) * 0.3
                + _eps_growth_score(eps_growth) * 0.3
            )
            scores[ticker] = round(score, 1)

            print(
                f"  [Fundamental] {ticker}: {score:.0f}점 "
                f"(PEG {peg or 'N/A'} / ROE {f'{roe*100:.1f}%' if roe else 'N/A'} / "
                f"EPS성장 {f'{eps_growth*100:.1f}%' if eps_growth else 'N/A'})"
            )

        except Exception as e:
            print(f"  [Fundamental] {ticker} 오류: {e}")
            scores[ticker] = 50.0  # 데이터 없으면 중립

    return scores
