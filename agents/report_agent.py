import os
import anthropic
from tools.stock_tool import get_stock_data
from tools.news_tool import get_news
from config import REPORT_LANGUAGE


def build_prompt(ticker: str, stock: dict, news: list[dict]) -> str:
    news_text = "\n".join(
        [f"- [{n['source']}] {n['headline']}" for n in news]
    ) or "관련 뉴스 없음"

    change_sign = "+" if stock["change_pct"] >= 0 else ""

    return f"""
종목: {stock['name']} ({ticker})
현재가: ${stock['price']} ({change_sign}{stock['change_pct']}%)
시가총액: ${stock.get('market_cap', 'N/A'):,}
PER: {stock.get('pe_ratio', 'N/A')}
52주 최고: ${stock.get('52w_high', 'N/A')} / 최저: ${stock.get('52w_low', 'N/A')}

최근 뉴스:
{news_text}

위 데이터를 바탕으로 {REPORT_LANGUAGE}로 간결한 투자 브리핑을 작성해주세요.
3~5문장으로 핵심만 정리해주세요.
""".strip()


def generate_report(tickers: list[str]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    reports = []
    for ticker in tickers:
        stock = get_stock_data(ticker)
        if "error" in stock:
            reports.append(f"### {ticker}\n데이터 수집 실패\n")
            continue

        news = get_news(ticker)
        prompt = build_prompt(ticker, stock, news)

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

        change_sign = "+" if stock["change_pct"] >= 0 else ""
        summary = message.content[0].text
        reports.append(
            f"### {stock['name']} ({ticker})\n"
            f"**${stock['price']} ({change_sign}{stock['change_pct']}%)**\n\n"
            f"{summary}\n"
        )

    return "\n---\n".join(reports)
