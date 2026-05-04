import os
import anthropic
from tools.stock_tool import get_stock_data
from tools.news_tool import get_news
from config import REPORT_LANGUAGE


def build_prompt(ticker: str, stock: dict, news: list[dict]) -> str:
    news_text = "\n".join(
        [f"- [{n['source']}] {n['headline']}" for n in news]
    ) or "관련 뉴스 없음"

    fmt = lambda v, prefix="", suffix="", decimals=2: (
        f"{prefix}{v:.{decimals}f}{suffix}" if isinstance(v, (int, float)) else "N/A"
    )

    return f"""
종목: {stock['name']} ({ticker}) | 섹터: {stock.get('sector', 'N/A')}
현재가: ${stock['price']} | 주간 등락률: {'+' if stock['weekly_change_pct'] >= 0 else ''}{stock['weekly_change_pct']}%
시가총액: {stock['market_cap']}
PER: {fmt(stock.get('pe_ratio'))} | Forward PER: {fmt(stock.get('forward_pe'))} | EPS: {fmt(stock.get('eps'), '$')}
52주 고가: {fmt(stock.get('52w_high'), '$')} | 52주 저가: {fmt(stock.get('52w_low'), '$')}
애널리스트 목표주가: {fmt(stock.get('target_price'), '$')}

최근 뉴스:
{news_text}

위 데이터를 바탕으로 {REPORT_LANGUAGE}로 아래 3개 항목을 각각 1~2문장으로 작성해주세요.
반드시 아래 형식을 지켜주세요:

[주목이유] (이번 주 왜 주목받고 있는지)
[핵심뉴스] (가장 중요한 뉴스 이슈)
[리스크] (투자 시 주의할 점)
""".strip()


def generate_report(tickers: list[str], scores: dict) -> list[dict]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    results = []
    for ticker in tickers:
        stock = get_stock_data(ticker)
        if "error" in stock:
            results.append({"ticker": ticker, "error": True})
            continue

        news = get_news(ticker)
        prompt = build_prompt(ticker, stock, news)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )

        analysis = _parse_analysis(message.content[0].text)

        results.append({
            "ticker": ticker,
            "stock": stock,
            "analysis": analysis,
            "scores": scores.get(ticker, {}),
        })

    return results


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
