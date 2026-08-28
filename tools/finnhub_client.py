import os
import threading
import time

import finnhub

# 무료 티어 한도는 60 calls/min. 여유를 두고 간격을 잡는다.
MIN_INTERVAL = 1.1
MAX_RETRIES = 4

_client = None
_client_lock = threading.Lock()
_pace_lock = threading.Lock()
_last_call = 0.0


def _get_client() -> finnhub.Client:
    global _client
    with _client_lock:
        if _client is None:
            _client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    return _client


def call(method: str, *args, **kwargs):
    """
    레이트리밋을 지키며 Finnhub API 를 호출하고, 429 는 백오프 후 재시도합니다.

    report_single 노드가 종목별로 병렬 실행되므로 호출이 여러 스레드에서
    동시에 발생합니다. 각 호출부에서 sleep 을 넣는 방식으로는 전체 호출
    속도를 통제할 수 없어, 프로세스 전역에서 간격을 강제합니다.
    """
    global _last_call

    for attempt in range(MAX_RETRIES):
        # 페이싱 구간만 잠그고 실제 호출은 잠금 밖에서 수행한다
        with _pace_lock:
            wait = MIN_INTERVAL - (time.monotonic() - _last_call)
            if wait > 0:
                time.sleep(wait)
            _last_call = time.monotonic()

        try:
            return getattr(_get_client(), method)(*args, **kwargs)
        except finnhub.FinnhubAPIException as e:
            if getattr(e, "status_code", None) != 429 or attempt == MAX_RETRIES - 1:
                raise
            backoff = 5 * (2 ** attempt)
            print(f"  [Finnhub] 429 — {backoff}초 후 재시도 ({attempt + 1}/{MAX_RETRIES})")
            time.sleep(backoff)
