import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Send

from tools.stock_tool import get_stock_data
from tools.langchain_tools import REPORT_TOOLS
from config import REPORT_LANGUAGE

# 도구 호출 왕복 상한. 모델이 질의만 바꿔 같은 도구를 계속 부르는 경우가 있어
# 상한에 닿으면 도구를 떼고 지금까지 모은 정보만으로 마무리시킨다.
MAX_TOOL_ROUNDS = 6


def dispatch_reports(state: dict) -> list[Send]:
    """각 종목을 병렬 report_single 노드로 분배합니다."""
    return [
        Send("report_single", {"ticker": t, "scores": state["scores"]})
        for t in state["tickers"]
    ]


def _run_tool(tool_map: dict, tool_call: dict) -> str:
    """
    도구를 실행하고 결과를 문자열로 반환합니다. 실패도 예외가 아니라 문자열입니다.

    Finnhub 429 처럼 외부 API 가 재시도까지 소진하면 여기서 예외가 올라오는데,
    그대로 두면 report_single → 그래프 전체가 중단되어 그 주 메일이 아예
    발송되지 않습니다. 한 종목의 도구 하나가 실패해도 모델이 다른 도구로
    복구할 수 있도록 실패 사유를 모델에게 되돌려줍니다.
    """
    name = tool_call["name"]
    print(f"    ↳ Tool 호출: {name}({tool_call['args']})")

    tool = tool_map.get(name)
    if tool is None:
        # 모델이 없는 도구명을 만들어낸 경우. KeyError 로 터뜨리지 않고 알려준다.
        print(f"      알 수 없는 도구: {name}")
        return f"'{name}' 도구는 존재하지 않습니다. 제공된 도구만 호출하세요."

    try:
        return str(tool.invoke(tool_call["args"]))
    except Exception as e:
        print(f"      {name} 실패: {type(e).__name__}: {e}")
        return f"도구 호출 실패({type(e).__name__}). 이 데이터 없이 진행하세요."


def _run_agent(ticker: str) -> str:
    """Tool-calling 루프를 돌려 최종 브리핑 텍스트를 반환합니다."""
    base_model = ChatAnthropic(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )
    model = base_model.bind_tools(REPORT_TOOLS)
    tool_map = {t.name: t for t in REPORT_TOOLS}

    messages = [
        HumanMessage(content=f"""
{ticker} 종목에 대한 투자 브리핑을 작성해주세요.
필요한 데이터는 제공된 도구를 사용해 직접 조회하세요.

사용 가능한 도구:
- stock_data_tool: 주가, PER, ROE 등 기본 데이터
- company_news_tool: 최근 뉴스 헤드라인
- sec_filing_tool: SEC 실적 공시 기반 실적·리스크 정보 (예: query="revenue growth risk factors")

최종 답변은 반드시 {REPORT_LANGUAGE}로 아래 형식만 사용하세요.
마크다운, 표, 이모지, 제목(#), 구분선(--)을 절대 사용하지 마세요.
각 항목은 반드시 대괄호 태그로 시작하고 1~2문장으로만 작성하세요:

[주목이유] 이번 주 왜 주목받고 있는지 1~2문장.
[핵심뉴스] 가장 중요한 뉴스 이슈 1~2문장.
[리스크] 투자 시 주의할 점 1~2문장.
""".strip())
    ]

    # Tool-calling 루프: Claude 가 도구를 더 부르지 않을 때까지 반복하되,
    # 종료 판정은 하네스가 한다(상한 없는 while 은 비용이 무한정 늘 수 있다).
    for round_no in range(MAX_TOOL_ROUNDS):
        response = model.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return response.content

        for tc in response.tool_calls:
            messages.append(
                ToolMessage(content=_run_tool(tool_map, tc), tool_call_id=tc["id"])
            )

    # 상한 도달: 도구를 떼고 한 번 더 불러 수집한 정보만으로 작성시킨다
    print(f"    ↳ 도구 호출 {MAX_TOOL_ROUNDS}회 초과 — 수집된 정보로 마무리")
    messages.append(HumanMessage(
        content="추가 도구 호출 없이, 지금까지 조회한 정보만으로 위 형식에 맞춰 작성하세요."
    ))
    return base_model.invoke(messages).content


def report_single(state: dict) -> dict:
    """
    LangChain Tool-calling 에이전트로 단일 종목을 분석합니다.
    Claude가 필요한 데이터(주가, 뉴스)를 스스로 판단해 Tool을 호출합니다.

    한 종목이 실패해도 error 플래그만 남기고 반환합니다. 예외를 올리면
    LangGraph 가 그래프 전체를 중단시켜 나머지 4종목 리포트와 메일까지
    사라지기 때문입니다.
    """
    ticker = state["ticker"]
    scores = state["scores"]

    print(f"  [ Report Node ] {ticker} 분석 중 (Tool-calling Agent)...")

    try:
        text = _run_agent(ticker)
    except Exception as e:
        print(f"  [ Report Node ] {ticker} 분석 실패: {type(e).__name__}: {e}")
        return {"report_items": [{"ticker": ticker, "error": True}]}

    # 이메일 렌더링용 구조화 데이터는 직접 수집 (LLM 응답과 별도)
    stock = get_stock_data(ticker)
    if "error" in stock:
        return {"report_items": [{"ticker": ticker, "error": True}]}

    analysis = _parse_analysis(text)

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
