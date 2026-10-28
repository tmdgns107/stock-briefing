"""
선정 이력에 사후 수익률을 붙여 신호별 유효성을 점검합니다.

    python -m tools.review                # 보유 4주 기준
    python -m tools.review --weeks 8

가중치 45/35/20 은 직관으로 정한 숫자입니다. 이 스크립트는 그 숫자가
맞는지 '측정'하기 위한 것이고, 판단은 사람이 합니다.

보유 기간을 고정하는 이유:
단순히 '선정 시점 가격 vs 현재 가격'으로 계산하면, 10주 전 기록은 10주
수익률이고 4주 전 기록은 4주 수익률이 되어 서로 비교할 수 없습니다.
그래서 각 기록마다 '선정일 ~ 선정일+N주' 구간의 주가를 따로 조회해
모든 종목을 같은 보유 기간으로 맞춥니다. 기간이 아직 지나지 않은
기록은 집계에서 제외합니다.
"""
import argparse
import json
import math
import os
import unicodedata
from datetime import datetime, timedelta, timezone

import yfinance as yf

from config import SELECTION_LOG_PATH

SIGNALS = ("volume", "fundamental", "buzz")
SIGNAL_LABELS = {"volume": "거래대금", "fundamental": "펀더멘털", "buzz": "버즈"}
# 이 미만에서는 상관계수가 우연에 좌우되므로 숫자를 믿지 말라고 경고한다
MIN_SAMPLES = 50


def _w(text: str) -> int:
    """표시 폭. 한글·전각 문자는 터미널에서 2칸을 차지한다."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int, right: bool = True) -> str:
    """전각을 고려해 폭을 맞춘다. f-string 의 :>8 은 글자 수로 세어 어긋난다."""
    gap = max(width - _w(text), 0)
    return " " * gap + text if right else text + " " * gap


def _load(path: str) -> list[dict]:
    if not os.path.exists(path):
        print(f"선정 이력이 없습니다: {path}")
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # JSONL 은 깨진 줄만 버리면 나머지를 살릴 수 있다
                print(f"  [review] {i}번째 줄 파싱 실패 — 건너뜀")
    return records


def _window_return(ticker: str, start: datetime, weeks: int) -> float | None:
    """선정일부터 weeks 주 뒤까지의 수익률(%). 조회 실패 시 None."""
    end = start + timedelta(weeks=weeks)
    try:
        # 선정일이 휴장일일 수 있어 앞뒤로 여유를 둔다
        hist = yf.Ticker(ticker).history(
            start=(start - timedelta(days=3)).date(),
            end=(end + timedelta(days=3)).date(),
        )
    except Exception as e:
        print(f"  [review] {ticker} 조회 실패: {type(e).__name__}")
        return None
    if hist.empty or len(hist) < 2:
        return None

    # 구간 내 첫 종가 → 보유 종료일 이전의 마지막 종가
    closes = hist["Close"]
    in_window = closes[closes.index.date <= end.date()]
    if len(in_window) < 2:
        return None
    entry, exit_ = in_window.iloc[0], in_window.iloc[-1]
    if not entry:
        return None
    return (exit_ - entry) / entry * 100


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if vx == 0 or vy == 0:
        return None          # 한쪽이 상수면 상관을 정의할 수 없다
    return cov / (vx * vy)


def review(weeks: int, path: str) -> None:
    records = _load(path)
    if not records:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    rows = []
    pending = 0

    for rec in records:
        run_at = datetime.fromisoformat(rec["run_at"])
        if run_at > cutoff:
            pending += 1          # 보유 기간이 아직 지나지 않음
            continue
        for pick in rec["picks"]:
            ret = _window_return(pick["ticker"], run_at, weeks)
            if ret is None:
                continue
            rows.append({**pick, "run_at": run_at.date().isoformat(), "ret": ret})

    print(f"\n=== 사후 성과 (보유 {weeks}주) ===")
    print(f"집계 대상 {len(rows)}종목 / 기간 미도달 {pending}회 실행분 제외")
    if not rows:
        print("아직 집계할 데이터가 없습니다.")
        return

    header = (
        _pad("선정일", 12, right=False) + _pad("티커", 7, right=False)
        + _pad("거래대금", 9) + _pad("펀더멘털", 10) + _pad("버즈", 7)
        + _pad("악재", 7) + _pad("수익률", 10)
    )
    print("\n" + header)
    for r in sorted(rows, key=lambda r: (r["run_at"], -r["ret"])):
        neg = r.get("negative_share") or 0
        print(
            _pad(r["run_at"], 12, right=False) + _pad(r["ticker"], 7, right=False)
            + _pad(f"{r['volume']:.0f}", 9) + _pad(f"{r['fundamental']:.0f}", 10)
            + _pad(f"{r['buzz']:.0f}", 7) + _pad(f"{neg:.0%}", 7)
            + _pad(f"{r['ret']:+.1f}%", 10)
        )

    returns = [r["ret"] for r in rows]
    wins = sum(1 for x in returns if x > 0)
    median = sorted(returns)[len(returns) // 2]
    print(f"\n평균 {sum(returns)/len(returns):+.1f}% / 중위 {median:+.1f}% / 승률 {wins}/{len(returns)}")

    print(f"\n신호별 상관 (Pearson, n={len(rows)})")
    for key in SIGNALS:
        corr = _pearson([r[key] for r in rows], returns)
        shown = f"{corr:+.2f}" if corr is not None else "계산 불가"
        print(f"  {_pad(SIGNAL_LABELS[key], 10, right=False)}{shown}")

    # 감쇠 계수(NEGATIVE_DAMPING)가 적절한지 보기 위한 분리 집계
    clean = [r["ret"] for r in rows if not (r.get("negative_share") or 0)]
    dirty = [r["ret"] for r in rows if (r.get("negative_share") or 0) > 0]
    print("\n악재 비중별")
    for label, group in (("악재 없음", clean), ("악재 있음", dirty)):
        if group:
            print(f"  {label}(n={len(group)}): 평균 {sum(group)/len(group):+.1f}%")
        else:
            print(f"  {label}(n=0): —")

    if len(rows) < MIN_SAMPLES:
        print(
            f"\n주의: n={len(rows)} 은 통계적 판단 근거가 되기 어렵습니다"
            f" (최소 {MIN_SAMPLES}건 권장). 지금 수치로 가중치를 바꾸지 마세요."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="선정 이력 사후 성과 점검")
    parser.add_argument("--weeks", type=int, default=4, help="보유 기간 (기본 4주)")
    parser.add_argument("--log", default=SELECTION_LOG_PATH, help="선정 이력 경로")
    args = parser.parse_args()
    review(args.weeks, args.log)


if __name__ == "__main__":
    main()
