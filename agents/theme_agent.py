import os
import json
import anthropic
from config import REPORT_LANGUAGE


def analyze_theme(report_items: list[dict]) -> dict:
    """
    선정된 종목 전체를 보고 이번 주 매크로 테마와 연쇄 효과를 분석합니다.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    stock_summary = "\n".join([
        f"- {item['stock']['name']} ({item['ticker']}) | 섹터: {item['stock'].get('sector','N/A')} | "
        f"주간 {'+' if item['stock']['weekly_change_pct'] >= 0 else ''}{item['stock']['weekly_change_pct']}%"
        for item in report_items if not item.get("error")
    ])

    prompt = f"""
이번 주 미국 주식 시장에서 거래량·검색량·뉴스 언급 기준으로 가장 주목받은 종목들입니다:

{stock_summary}

위 종목들을 종합적으로 분석해서 {REPORT_LANGUAGE}로 아래 JSON 형식으로 답해주세요.
다른 텍스트 없이 JSON만 출력하세요.

{{
  "theme_title": "이번 주 핵심 테마 (10자 이내)",
  "theme_summary": "테마 요약 설명 (2문장)",
  "beneficiary_sectors": [
    {{"sector": "섹터명", "reason": "수혜 이유 (1문장)", "examples": ["종목1", "종목2"]}}
  ],
  "risk_sectors": [
    {{"sector": "섹터명", "reason": "주의 이유 (1문장)"}}
  ],
  "watch_stocks": [
    {{"ticker": "티커", "name": "종목명", "reason": "관심 이유 (1문장)"}}
  ]
}}

beneficiary_sectors는 2~3개, risk_sectors는 1~2개, watch_stocks는 3개로 작성해주세요.
""".strip()

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "theme_title": "분석 실패",
            "theme_summary": raw,
            "beneficiary_sectors": [],
            "risk_sectors": [],
            "watch_stocks": [],
        }
