"""
선정 결과를 JSONL 로 누적합니다.

가중치 45/35/20 은 지금 직관으로 정한 숫자이고, 맞는지 확인할 방법이
없었습니다. 실행이 끝나면 선정 결과가 사라져서 '어느 신호가 실제로
유효했는지' 되짚을 근거가 남지 않기 때문입니다.

선정 시점의 신호별 점수와 주가를 남겨두면, 나중에 같은 티커의 주가를
조회해 사후 수익률을 붙일 수 있습니다. 그때 비로소 가중치 조정이
추측이 아니라 측정이 됩니다.

기록 실패는 절대 본 실행을 막지 않습니다. 부가 기능이 본 기능을
중단시키면 안 됩니다.
"""
import json
import os
from datetime import datetime, timezone

from config import SELECTION_LOG_PATH


def append_selection(
    tickers: list[str],
    scores: dict,
    sectors: dict,
    prices: dict,
    buzz_meta: dict,
) -> None:
    record = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "picks": [
            {
                "ticker": t,
                "sector": sectors.get(t, "기타"),
                "price_at_pick": prices.get(t),
                "total": scores[t]["total"],
                "volume": scores[t]["volume"],
                "fundamental": scores[t]["fundamental"],
                "buzz": scores[t]["buzz"],
                # 사후 분석에서 '악재로 뜬 종목의 성과'를 따로 볼 수 있게 남긴다
                "buzz_ratio": buzz_meta.get(t, {}).get("ratio"),
                "negative_share": buzz_meta.get(t, {}).get("negative_share"),
            }
            for t in tickers
        ],
    }

    try:
        os.makedirs(os.path.dirname(SELECTION_LOG_PATH) or ".", exist_ok=True)
        with open(SELECTION_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"  선정 이력 기록: {SELECTION_LOG_PATH}")
    except Exception as e:
        print(f"  [SelectionLog] 기록 실패(무시): {type(e).__name__}: {e}")
