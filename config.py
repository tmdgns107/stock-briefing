TOP_N = 5                               # 최종 분석할 종목 수
REPORT_LANGUAGE = "Korean"
MAX_MARKET_CAP = 500_000_000_000        # 시총 상한선 ($500B) — 초대형주는 변별력이 낮아 제외
MIN_MARKET_CAP = 2_000_000_000          # 시총 하한선 ($2B) — 마이크로캡·작전주 제외
CANDIDATE_POOL = 250                    # 스크리너에서 받아올 후보 수 (Yahoo 최대치)
MIN_DOLLAR_VOLUME = 300_000_000         # 일 거래대금 하한 ($3억) — 유동성 절대 기준
SCORING_POOL = 20                       # 신호를 측정할 후보 수 (늘리면 API 호출 시간 증가)

# 선정 신호 가중치 (합 1.0)
WEIGHT_VOLUME = 0.45                    # 거래대금
WEIGHT_FUNDAMENTAL = 0.35               # PEG·ROE·EPS 성장
WEIGHT_BUZZ = 0.20                      # 뉴스 급증 배수 (평소 대비)

MAX_PER_SECTOR = 2                      # 한 섹터에서 선정할 최대 종목 수 (편중 방지)
NEGATIVE_DAMPING = 0.4                  # 악재 비중 100%일 때 버즈에 곱할 계수
FUNDAMENTAL_PRIOR = 40.0                # 펀더멘털 결측 시 수축(shrink)시킬 기준값
LLM_MODEL = "claude-opus-5"             # 노드에서 공용으로 쓰는 Claude 모델

SELECTION_LOG_PATH = "data/selections.jsonl"   # 선정 이력 (사후 성과 검증용)
