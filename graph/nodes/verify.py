import os
import anthropic
from pydantic import BaseModel

from tools.rag_tool import search as rag_search
from config import LLM_MODEL, REPORT_LANGUAGE


class Verdict(BaseModel):
    ticker: str
    supported: bool
    reason: str


class VerifyResult(BaseModel):
    verdicts: list[Verdict]


def verify_node(state: dict) -> dict:
    """
    리포트의 [리스크] 주장이 SEC 10-Q 공시 근거로 뒷받침되는지 교차 검증합니다.
    RAG에 근거가 없는 주장(할루시네이션)을 잡아내는 것이 목적입니다.
    """
    print("\n[ Verify Node ] 리포트 근거 검증 중...")

    targets = [
        item for item in state["report_items"]
        if not item.get("error") and item.get("analysis", {}).get("리스크")
    ]
    if not targets:
        print("  검증할 항목 없음")
        return {"verifications": {}}

    evidence = "\n\n".join(
        f"[{item['ticker']}]\n"
        f"리포트 주장: {item['analysis']['리스크']}\n"
        f"공시 근거: {rag_search(item['ticker'], item['analysis']['리스크'], n_results=8)[:4000]}"
        for item in targets
    )

    prompt = f"""
아래는 종목별 투자 리포트의 '리스크' 주장과, 해당 종목의 SEC 10-Q 공시에서 검색된 근거입니다.
각 종목에 대해 리포트 주장이 공시 근거로 뒷받침되는지 판정해 주세요.

판정 기준:
- 공시 근거가 주장을 직접 뒷받침하면 supported=true
- 공시 근거에 관련 내용이 없거나 주장과 어긋나면 supported=false
- 근거가 "관련 공시 내용 없음"이면 supported=false
- 추측으로 보완하지 말고 제시된 근거만으로 판정하세요

reason은 {REPORT_LANGUAGE}로 판정 이유를 한 문장으로 작성하세요.
ticker는 아래 대괄호 안의 티커를 그대로 사용하세요.

{evidence}
""".strip()

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.parse(
            model=LLM_MODEL,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            output_format=VerifyResult,
        )
        verdicts = response.parsed_output.verdicts
    except Exception as e:
        print(f"  [Verify Node] 검증 실패: {type(e).__name__}: {e}")
        return {"verifications": {}}

    for v in verdicts:
        mark = "근거 확인" if v.supported else "근거 부족"
        print(f"  {v.ticker}: {mark} — {v.reason}")

    return {"verifications": {v.ticker: v.model_dump() for v in verdicts}}
