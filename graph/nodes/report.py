import os
import anthropic
from langgraph.types import Send
from tools.stock_tool import get_stock_data
from tools.news_tool import get_news
from config import REPORT_LANGUAGE


def dispatch_reports(state: dict) -> list[Send]:
    """각 종목을 병렬 report_single 노드로 분배합니다."""
    return [
        Send("report_single", {"ticker": t, "scores": state["scores"]})
        for t in state["tickers"]
    ]


def report_single(state: dict) -> dict:
    """단일 종목 AI 분석 — 병렬로 실행됩니다."""
    ticker = state["ticker"]
    scores = state["scores"]

    print(f"  [ Report Node ] {ticker} 분석 중...")

    stock = get_stock_data(ticker)
    if "error" in stock:
        return {"report_items": [{"ticker": ticker, "error": True}]}

    news = get_news(ticker)
    prompt = _build_prompt(ticker, stock, news)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis = _parse_analysis(message.content[0].text)

    return {
        "report_items": [{
            "ticker": ticker,
            "stock": stock,
            "analysis": analysis,
            "scores": scores.get(ticker, {}),
        }]
    }


def _build_prompt(ticker: str, stock: dict, news: list[dict]) -> str:
    news_text = "\n".join(
        [f"- [{n['source']}] {n['headline']}" for n in news]
    ) or "관련 뉴스 없음"

    fmt = lambda v, prefix="", suffix="", d=2: (
        f"{prefix}{v:.{d}f}{suffix}" if isinstance(v, (int, float)) else "N/A"
    )
    roe_raw = stock.get("roe")
    roe = f"{roe_raw * 100:.1f}%" if isinstance(roe_raw, (int, float)) else "N/A"

    return f"""
종목: {stock['name']} ({ticker}) | 섹터: {stock.get('sector', 'N/A')}
현재가: ${stock['price']} | 주간 등락률: {'+' if stock['weekly_change_pct'] >= 0 else ''}{stock['weekly_change_pct']}%
시가총액: {stock['market_cap']} | ROE: {roe}
PER: {fmt(stock.get('pe_ratio'))} | Forward PER: {fmt(stock.get('forward_pe'))} | EPS: {fmt(stock.get('eps'), '$')}
52주 고가: {fmt(stock.get('52w_high'), '$')} | 52주 저가: {fmt(stock.get('52w_low'), '$')}
애널리스트 목표주가: {fmt(stock.get('target_price'), '$')}

최근 뉴스:
{news_text}

{REPORT_LANGUAGE}로 아래 3개 항목을 각각 1~2문장으로 작성하세요.

[주목이유] (이번 주 왜 주목받고 있는지)
[핵심뉴스] (가장 중요한 뉴스 이슈)
[리스크] (투자 시 주의할 점)
""".strip()


def _parse_analysis(text: str) -> dict:
    sections = {"주목이유": "", "핵심뉴스": "", "리스크": ""}
    current = None
    for line in text.splitlines():
        line = line.strip()
        for key in sections:
            if line.startswith(f"[{key}]"):
                current = key
                line = line[len(f"[{key}]"):].strip()
                break
        if current and line:
            sections[current] += (" " if sections[current] else "") + line
    return sections
