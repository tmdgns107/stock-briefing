from tools.rag_tool import ingest_ticker


def rag_node(state: dict) -> dict:
    print("\n[ RAG Node ] SEC 10-Q 공시 수집 중...")
    for ticker in state["tickers"]:
        ingest_ticker(ticker)
    return {}
