import html
import re
import requests
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

_collection = None
_ticker_map = None
_source_forms: dict[str, str] = {}   # 티커 → 색인에 사용한 서식

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


# 우선순위: 분기 실적 서술이 있는 서식부터. 외국 기업(foreign private issuer)은
# 10-Q 를 제출하지 않고 6-K(분기)·20-F(연간)를 제출한다.
FILING_PRIORITY = ("10-Q", "6-K", "20-F")
MAX_6K_ATTEMPTS = 6          # 6-K 는 보도자료가 많아 분기 실적 건이 몇 칸 뒤에 있다
MAX_EXHIBITS = 2             # 한 건당 확인할 첨부 수
MIN_EXHIBIT_BYTES = 10_000   # 이보다 작으면 표지·서명 페이지
MAX_EXHIBIT_BYTES = 2_000_000  # 이보다 크면 재무제표 표 덤프
MIN_PROSE_SCORE = 4          # 이 미만이면 실적 서술이 아닌 보도자료로 간주
GOOD_PROSE_SCORE = 8         # 이 이상이면 더 찾지 않고 채택

# 실적 서술 문서인지 판별하는 키워드
_PROSE_HINTS = (
    r"results of operations",
    r"operating and financial review",
    r"management.{0,30}discussion",
    r"revenue (increased|decreased|grew)",
)


def _submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    res = requests.get(url, headers=HEADERS, timeout=20)
    return res.json().get("filings", {}).get("recent", {})


def _prose_score(text: str) -> int:
    return sum(len(re.findall(p, text, re.IGNORECASE)) for p in _PROSE_HINTS)


def _best_exhibit_url(
    cik: str, accession: str, primary: str
) -> tuple[int, str] | None:
    """
    6-K 본문은 대개 표지뿐이고 실제 실적 서술은 EX-99 첨부에 있습니다.
    첨부 중 서술이 가장 풍부한 문서의 (점수, URL) 을 반환합니다.
    """
    acc_clean = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}"
    try:
        items = requests.get(f"{base}/index.json", headers=HEADERS, timeout=20).json()
        files = items["directory"]["item"]
    except Exception:
        return None

    candidates = [
        f for f in files
        if f["name"].endswith(".htm")
        and f["name"] != primary
        and "index" not in f["name"]
        and MIN_EXHIBIT_BYTES <= int(f.get("size") or 0) <= MAX_EXHIBIT_BYTES
    ]
    # 재무제표 덤프는 크고 표 위주라, 작은 것부터 확인한다
    candidates.sort(key=lambda f: int(f.get("size") or 0))

    best, best_score = None, 0
    for f in candidates[:MAX_EXHIBITS]:
        url = f"{base}/{f['name']}"
        try:
            text = _strip_html(requests.get(url, headers=HEADERS, timeout=30).text)
        except Exception:
            continue
        score = _prose_score(text)
        if score > best_score:
            best, best_score = url, score

    return (best_score, best) if best else None


def _find_filing(cik: str) -> tuple[str, str] | None:
    """(서식, 문서 URL) 을 우선순위대로 찾습니다."""
    filings = _submissions(cik)
    forms = filings.get("form", [])
    accessions = filings.get("accessionNumber", [])
    primaries = filings.get("primaryDocument", [])
    if not forms:
        return None

    for wanted in FILING_PRIORITY:
        attempts = 0
        six_k_candidates: list[tuple[int, str]] = []
        for form, acc, primary in zip(forms, accessions, primaries):
            if form != wanted:
                continue

            acc_clean = acc.replace("-", "")
            base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}"

            if wanted == "6-K":
                attempts += 1
                if attempts > MAX_6K_ATTEMPTS:
                    break
                # 6-K 에는 분기 실적 외에 사채 발행 등 보도자료도 섞여 있다.
                # 첫 건을 바로 쓰지 않고 후보를 모아 가장 서술이 풍부한 것을 고른다.
                cand = _best_exhibit_url(cik, acc, primary)
                if cand:
                    six_k_candidates.append(cand)
                    if cand[0] >= GOOD_PROSE_SCORE:
                        return wanted, cand[1]
                continue

            # 전체 제출본(.txt)은 첨부까지 포함해 수십 MB → 본문 문서만 사용
            doc = f"{base}/{primary}" if primary else f"{base}/{acc}.txt"
            return wanted, doc

        if wanted == "6-K" and six_k_candidates:
            best_score, best_url = max(six_k_candidates)
            if best_score >= MIN_PROSE_SCORE:
                return wanted, best_url

    return None


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s{3,}", "\n", text)


# 10-Q 는 MD&A, 20-F 는 'Operating and Financial Review and Prospects' 가 같은 역할
_SECTION_START = r"(management.{0,30}discussion.{0,60}analysis|operating and financial review and prospects)"
_SECTION_END = r"(quantitative.{0,30}qualitative|item\s+[36])"


def _fetch_filing_text(url: str) -> str:
    try:
        text = _strip_html(requests.get(url, headers=HEADERS, timeout=30).text)

        # 첫 매치는 대개 목차이므로 가장 긴 본문 매치를 선택
        bodies = [
            m.group(2)
            for m in re.finditer(
                _SECTION_START + r"(.*?)" + _SECTION_END,
                text, re.IGNORECASE | re.DOTALL,
            )
        ]
        if bodies:
            return max(bodies, key=len).strip()[:15000]
        # 6-K 첨부처럼 문서 전체가 실적 서술인 경우 섹션 구분이 없다
        return text[:15000]
    except Exception:
        return ""


def ingest_ticker(ticker: str) -> str | None:
    """
    종목의 최신 실적 공시를 색인하고, 사용한 서식명을 반환합니다.
    공시를 찾지 못하면 None 을 반환합니다(검증 노드가 '대조 불가'로 구분).
    """
    collection = _get_collection()

    # 이미 수집된 경우 스킵
    if collection.get(where={"ticker": ticker})["ids"]:
        return _source_forms.get(ticker, "기존 색인")

    cik = _get_cik(ticker)
    if not cik:
        print(f"    [RAG] {ticker}: CIK 조회 실패")
        return None

    found = _find_filing(cik)
    if not found:
        print(f"    [RAG] {ticker}: 실적 공시 없음 (10-Q/6-K/20-F 미확인)")
        return None
    form, filing_url = found

    text = _fetch_filing_text(filing_url)
    if not text:
        print(f"    [RAG] {ticker}: {form} 본문 수집 실패")
        return None

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    collection.add(
        documents=chunks,
        metadatas=[{"ticker": ticker, "form": form} for _ in chunks],
        ids=[f"{ticker}_{i}" for i in range(len(chunks))],
    )
    _source_forms[ticker] = form
    print(f"    [RAG] {ticker}: {len(chunks)}개 청크 저장 완료 ({form})")
    return form


def get_source_form(ticker: str) -> str | None:
    """색인에 사용한 서식명. 공시를 찾지 못한 종목은 None."""
    return _source_forms.get(ticker)


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
