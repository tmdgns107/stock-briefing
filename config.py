TOP_N = 5                               # 최종 분석할 종목 수
REPORT_LANGUAGE = "Korean"
MAX_MARKET_CAP = 500_000_000_000        # 시총 상한선 ($500B) — 초대형주는 변별력이 낮아 제외
MIN_MARKET_CAP = 2_000_000_000          # 시총 하한선 ($2B) — 마이크로캡·작전주 제외
CANDIDATE_POOL = 250                    # 스크리너에서 받아올 후보 수 (Yahoo 최대치)

# 선정 신호 가중치 (합 1.0)
WEIGHT_VOLUME = 0.45                    # 거래대금
WEIGHT_FUNDAMENTAL = 0.35               # PEG·ROE·EPS 성장
WEIGHT_BUZZ = 0.20                      # 종목 뉴스 건수
LLM_MODEL = "claude-opus-5"             # 노드에서 공용으로 쓰는 Claude 모델
