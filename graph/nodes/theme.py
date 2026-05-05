import os
import json
import re
import anthropic
from config import REPORT_LANGUAGE


def theme_node(state: dict) -> dict:
    print("\n[ Theme Node ] 매크로 테마 분석 중...")

    report_items = state["report_items"]
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    stock_summary = "\n".join([
        f"- {item['stock']['name']} ({item['ticker']}) | 섹터: {item['stock'].get('sector','N/A')} | "
        f"주간 {'+' if item['stock']['weekly_change_pct'] >= 0 else ''}{item['stock']['weekly_change_pct']}%"
        for item in report_items if not item.get("error")
    ])

    prompt = f"""
이번 주 미국 주식 시장에서 가장 주목받은 종목들입니다:

{stock_summary}

{REPORT_LANGUAGE}로 아래 JSON만 출력하세요. 설명 텍스트 없이 JSON만 작성하세요.

{{
  "theme_title": "핵심 테마 (10자 이내)",
  "theme_summary": "테마 요약 2문장",
  "beneficiary_sectors": [
    {{"sector": "섹터명", "reason": "수혜 이유 1문장", "examples": ["티커1", "티커2"]}}
  ],
  "risk_sectors": [
    {{"sector": "섹터명", "reason": "주의 이유 1문장"}}
  ],
  "watch_stocks": [
    {{"ticker": "티커", "name": "종목명", "reason": "관심 이유 1문장"}}
  ]
}}

규칙: beneficiary_sectors 2개, risk_sectors 1개, watch_stocks 3개.
""".strip()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = re.sub(r"^```(?:json)?\s*", "", message.content[0].text.strip())
    raw = re.sub(r"\s*```$", "", raw).strip()

    try:
        theme = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                theme = json.loads(match.group())
            except json.JSONDecodeError:
                theme = _fallback_theme(raw)
        else:
            theme = _fallback_theme(raw)

    print(f"  → 테마: {theme.get('theme_title')}")
    return {"theme": theme}


def _fallback_theme(raw: str) -> dict:
    print(f"[Theme Node] JSON 파싱 실패:\n{raw}")
    return {
        "theme_title": "분석 중",
        "theme_summary": "이번 주 주목받은 종목들의 테마 분석 중 오류가 발생했습니다.",
        "beneficiary_sectors": [],
        "risk_sectors": [],
        "watch_stocks": [],
    }
