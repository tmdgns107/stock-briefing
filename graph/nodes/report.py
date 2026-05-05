import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Send

from tools.stock_tool import get_stock_data
from tools.langchain_tools import REPORT_TOOLS
from config import REPORT_LANGUAGE


def dispatch_reports(state: dict) -> list[Send]:
    """각 종목을 병렬 report_single 노드로 분배합니다."""
    return [
        Send("report_single", {"ticker": t, "scores": state["scores"]})
        for t in state["tickers"]
    ]


def report_single(state: dict) -> dict:
    """
    LangChain Tool-calling 에이전트로 단일 종목을 분석합니다.
    Claude가 필요한 데이터(주가, 뉴스)를 스스로 판단해 Tool을 호출합니다.
    """
    ticker = state["ticker"]
    scores = state["scores"]

    print(f"  [ Report Node ] {ticker} 분석 중 (Tool-calling Agent)...")

    model = ChatAnthropic(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        api_key=os.environ["ANTHROPIC_API_KEY"],
    ).bind_tools(REPORT_TOOLS)
    tool_map = {t.name: t for t in REPORT_TOOLS}

    messages = [
        HumanMessage(content=f"""
{ticker} 종목에 대한 투자 브리핑을 작성해주세요.
필요한 데이터는 제공된 도구를 사용해 직접 조회하세요.

최종 답변은 반드시 {REPORT_LANGUAGE}로 아래 형식만 사용하세요.
마크다운, 표, 이모지, 제목(#), 구분선(--)을 절대 사용하지 마세요.
각 항목은 반드시 대괄호 태그로 시작하고 1~2문장으로만 작성하세요:

[주목이유] 이번 주 왜 주목받고 있는지 1~2문장.
[핵심뉴스] 가장 중요한 뉴스 이슈 1~2문장.
[리스크] 투자 시 주의할 점 1~2문장.
""".strip())
    ]

    # Tool-calling 루프: Claude가 필요한 도구를 모두 호출할 때까지 반복
    while True:
        response = model.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            result = tool_map[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
            print(f"    ↳ Tool 호출: {tc['name']}({tc['args']})")

    # 이메일 렌더링용 구조화 데이터는 직접 수집 (LLM 응답과 별도)
    stock = get_stock_data(ticker)
    if "error" in stock:
        return {"report_items": [{"ticker": ticker, "error": True}]}

    analysis = _parse_analysis(response.content)

    return {
        "report_items": [{
            "ticker": ticker,
            "stock": stock,
            "analysis": analysis,
            "scores": scores.get(ticker, {}),
        }]
    }


def _parse_analysis(text: str) -> dict:
    import re
    sections = {"주목이유": "", "핵심뉴스": "", "리스크": ""}
    # Flexible key aliases to handle spacing/emoji variations
    key_aliases = {
        "주목이유": ["주목이유", "주목 이유"],
        "핵심뉴스": ["핵심뉴스", "핵심 뉴스"],
        "리스크": ["리스크"],
    }
    current = None
    for line in text.splitlines():
        line = line.strip()
        # Strip leading markdown markers: ##, >, -, *, 🔍 etc.
        clean = re.sub(r'^[#>\-\*\s🔍📰⚠️📌]+', '', line).strip()
        matched_key = None
        for key, aliases in key_aliases.items():
            for alias in aliases:
                if clean.startswith(f"[{alias}]"):
                    matched_key = key
                    clean = clean[len(f"[{alias}]"):].strip()
                    break
            if matched_key:
                break
        if matched_key:
            current = matched_key
        if current and clean:
            sections[current] += (" " if sections[current] else "") + clean
    return sections
