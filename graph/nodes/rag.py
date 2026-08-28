from tools.rag_tool import ingest_ticker


def rag_node(state: dict) -> dict:
    print("\n[ RAG Node ] SEC 실적 공시 수집 중...")

    forms = {}
    for ticker in state["tickers"]:
        forms[ticker] = ingest_ticker(ticker)

    missing = [t for t, f in forms.items() if f is None]
    if missing:
        print(f"  공시 미확인: {', '.join(missing)} (검증에서 '대조 불가'로 처리)")

    return {}
