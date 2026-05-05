import json
from langchain_core.tools import tool
from tools.stock_tool import get_stock_data
from tools.news_tool import get_news
from tools.rag_tool import search as rag_search


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


@tool
def sec_filing_tool(ticker: str, query: str) -> str:
    """
    종목의 최신 SEC 10-Q 공시(분기 보고서) MD&A 섹션에서 query와 관련된 내용을 검색합니다.
    실적, 리스크 팩터, 사업 현황 등 공시 기반 정보가 필요할 때 사용하세요.
    """
    return rag_search(ticker, query)


REPORT_TOOLS = [stock_data_tool, company_news_tool, sec_filing_tool]
