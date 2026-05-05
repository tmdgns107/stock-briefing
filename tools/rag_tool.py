import re
import requests
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain.text_splitter import RecursiveCharacterTextSplitter

_collection = None

HEADERS = {"User-Agent": "stock-briefing/1.0 hooon107@gmail.com"}


def _get_collection():
    global _collection
    if _collection is None:
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.Client()
        _collection = client.get_or_create_collection("sec_filings", embedding_function=ef)
    return _collection


def _get_cik(ticker: str) -> str | None:
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-Q&dateRange=custom&startdt=2023-01-01"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        hits = res.json().get("hits", {}).get("hits", [])
        if hits:
            return hits[0]["_source"].get("entity_id", "").lstrip("0")
    except Exception:
        pass

    # fallback: ticker → CIK lookup via company_tickers.json
    try:
        res = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=HEADERS, timeout=10
        )
        for entry in res.json().values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry["cik_str"])
    except Exception:
        pass
    return None


def _get_latest_10q_url(cik: str) -> str | None:
    padded = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        filings = res.json().get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        for form, acc in zip(forms, accessions):
            if form == "10-Q":
                acc_clean = acc.replace("-", "")
                return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/{acc}.txt"
    except Exception:
        pass
    return None


def _fetch_filing_text(url: str) -> str:
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        text = res.text
        # 태그 제거 및 연속 공백 정리
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s{3,}", "\n", text)
        # MD&A 섹션만 추출 (없으면 전체 앞부분)
        match = re.search(
            r"(management.{0,30}discussion.{0,60}analysis)(.*?)(quantitative.{0,30}qualitative|item\s+3)",
            text, re.IGNORECASE | re.DOTALL
        )
        return match.group(2).strip()[:15000] if match else text[:15000]
    except Exception:
        return ""


def ingest_ticker(ticker: str) -> bool:
    collection = _get_collection()

    # 이미 수집된 경우 스킵
    existing = collection.get(where={"ticker": ticker})
    if existing["ids"]:
        return True

    cik = _get_cik(ticker)
    if not cik:
        print(f"    [RAG] {ticker}: CIK 조회 실패")
        return False

    filing_url = _get_latest_10q_url(cik)
    if not filing_url:
        print(f"    [RAG] {ticker}: 10-Q URL 조회 실패")
        return False

    text = _fetch_filing_text(filing_url)
    if not text:
        print(f"    [RAG] {ticker}: 공시 본문 수집 실패")
        return False

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    collection.add(
        documents=chunks,
        metadatas=[{"ticker": ticker} for _ in chunks],
        ids=[f"{ticker}_{i}" for i in range(len(chunks))],
    )
    print(f"    [RAG] {ticker}: {len(chunks)}개 청크 저장 완료 (10-Q MD&A)")
    return True


def search(ticker: str, query: str, n_results: int = 3) -> str:
    collection = _get_collection()
    try:
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"ticker": ticker},
        )
        docs = results.get("documents", [[]])[0]
        if not docs:
            return "관련 공시 내용 없음"
        return "\n---\n".join(docs)
    except Exception as e:
        return f"RAG 검색 오류: {e}"
