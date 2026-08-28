import operator
from typing import Annotated
from typing_extensions import TypedDict


class BriefingState(TypedDict):
    tickers: list[str]
    scores: dict
    report_items: Annotated[list[dict], operator.add]  # 병렬 노드 결과 누적
    theme: dict
    verifications: dict                        # 티커 → 공시 근거 검증 결과
