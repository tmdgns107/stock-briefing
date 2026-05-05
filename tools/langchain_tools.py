import json
from langchain_core.tools import tool
from tools.stock_tool import get_stock_data
from tools.news_tool import get_news


@tool
def stock_data_tool(ticker: str) -> str:
    """
    종목의 현재가, 주간 등락률, 시가총액, PER, Forward PER,
    EPS, ROE, 52주 고저가, 애널리스트 목표주가를 조회합니다.
    """
    data = get_stock_data(ticker)
    return json.dumps(data, ensure_ascii=False, default=str)


@tool
def company_news_tool(ticker: str) -> str:
    """
    종목의 최근 7일 뉴스 헤드라인과 요약을 조회합니다.
    """
    news = get_news(ticker)
    if not news:
        return "관련 뉴스 없음"
    return "\n".join([
        f"- [{n['source']}] {n['headline']}"
        for n in news
    ])


REPORT_TOOLS = [stock_data_tool, company_news_tool]
