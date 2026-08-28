import html
import re
import requests
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

_collection = None
_ticker_map = None

HEADERS = {"User-Agent": "stock-briefing/1.0 hooon107@gmail.com"}


def _get_collection():
    global _collection
    if _collection is None:
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        client = chromadb.Client()
        _collection = client.get_or_create_collection("sec_filings", embedding_function=ef)
    return _collection


def _get_ticker_map() -> dict:
    """SEC 공식 ticker → CIK 매핑 (프로세스 내 1회만 다운로드)"""
    global _ticker_map
    if _ticker_map is None:
        try:
            res = requests.get(
                "https://www.sec.gov/files/company_tickers.json",
                headers=HEADERS, timeout=20
            )
            _ticker_map = {
                e["ticker"].upper(): str(e["cik_str"])
                for e in res.json().values() if e.get("ticker")
            }
        except Exception:
            _ticker_map = {}
    return _ticker_map


def _get_cik(ticker: str) -> str | None:
    cik = _get_ticker_map().get(ticker.upper())
    if cik:
        return cik

    # fallback: EDGAR 전문 검색 결과의 ciks 필드 사용
    url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&forms=10-Q"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        for hit in res.json().get("hits", {}).get("hits", []):
            names = " ".join(hit["_source"].get("display_names", []))
            ciks = hit["_source"].get("ciks", [])
            if ciks and f"({ticker.upper()})" in names.upper():
                return ciks[0].lstrip("0")
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
        primaries = filings.get("primaryDocument", [])
        for form, acc, primary in zip(forms, accessions, primaries):
            if form == "10-Q":
                acc_clean = acc.replace("-", "")
                base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}"
                # 전체 제출본(.txt)은 첨부문서까지 포함해 수십 MB → 본문 문서만 사용
                return f"{base}/{primary}" if primary else f"{base}/{acc}.txt"
    except Exception:
        pass
    return None


def _fetch_filing_text(url: str) -> str:
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        text = res.text
        # 태그 제거 및 연속 공백 정리
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s{3,}", "\n", text)
        # MD&A 섹션 추출 — 첫 매치는 대개 목차이므로 가장 긴 본문 매치를 선택
        bodies = [
            m.group(2)
            for m in re.finditer(
                r"(management.{0,30}discussion.{0,60}analysis)(.*?)"
                r"(quantitative.{0,30}qualitative|item\s+3)",
                text, re.IGNORECASE | re.DOTALL,
            )
        ]
        if bodies:
            return max(bodies, key=len).strip()[:15000]
        return text[:15000]
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
