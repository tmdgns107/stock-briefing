# 📈 Stock Briefing

매주 토요일 오전 10시, AI가 이번 주 가장 주목받은 미국주식을 자동으로 선정하고 투자 브리핑을 이메일로 발송하는 에이전트입니다.

---

## 주요 기능

- **AI 종목 자동 발굴** — 거래금액·펀더멘털·뉴스 버즈·언급 빈도 4가지 신호를 종합해 이번 주 TOP 5 종목 자동 선정
- **LangChain Tool-calling 분석** — Claude가 필요한 데이터를 스스로 판단해 도구를 호출하고 종목별 투자 브리핑 생성
- **RAG 기반 공시 분석** — SEC 10-Q(분기 보고서) MD&A 섹션을 ChromaDB에 벡터 저장, Claude가 의미 기반 검색으로 공시 근거 활용
- **LangGraph 병렬 오케스트레이션** — 종목별 분석을 병렬 실행, 전체 처리 시간 단축
- **매크로 테마 분석** — 선정 종목들을 관통하는 주간 투자 테마 및 섹터 동향 자동 도출
- **이메일 자동 발송** — 매주 토요일 오전 10시 Gmail로 HTML 리포트 발송
- **무서버 운영** — GitHub Actions 기반, 별도 서버 없이 완전 자동화

---

## AI Workflow 아키텍처

```
[GitHub Actions — 매주 토요일 10:00 KST]
              │
              ▼
        ┌─────────────┐
        │   main.py   │  진입점 (LangGraph 실행)
        └──────┬──────┘
               │
               ▼
   ┌───────────────────────────────┐
   │       Discovery Node          │  종목 자동 발굴
   └──────────────┬────────────────┘
                  │  4가지 신호 가중 합산 → TOP 5 선정
       ┌──────────┼──────────┬──────────┐
       ▼          ▼          ▼          ▼
  ┌─────────┐ ┌────────┐ ┌───────┐ ┌─────────┐
  │거래금액  │ │펀더멘털│ │뉴스   │ │시장 언급│
  │(Yahoo)  │ │(PEG/ROE│ │버즈   │ │(Finnhub)│
  │  40%    │ │ EPS)   │ │20%    │ │  10%    │
  │         │ │  30%   │ │       │ │         │
  └─────────┘ └────────┘ └───────┘ └─────────┘
                  │
                  ▼
   ┌──────────────────────────┐
   │        RAG Node          │  SEC 10-Q 공시 수집 · 벡터 저장
   │  (ChromaDB + 임베딩)     │  MD&A 섹션 → ChromaDB 인메모리
   └──────────────┬───────────┘
                  │
       ┌──────────┼──────────┐  LangGraph Send API
       ▼          ▼          ▼  (병렬 실행)
  ┌─────────┐ ┌────────┐ ┌───────┐
  │ Report  │ │ Report │ │Report │  종목별 AI 분석
  │ Single  │ │ Single │ │Single │
  └────┬────┘ └───┬────┘ └───┬───┘
       │          │          │
       │  LangChain Tool-calling Agent
       │  Claude가 필요한 도구를 스스로 결정
       ├──→ stock_data_tool (yfinance)
       ├──→ company_news_tool (Finnhub)
       └──→ sec_filing_tool (ChromaDB RAG)
                  │
                  ▼  병렬 완료 후 합류
   ┌──────────────────────────┐
   │       Theme Node         │  매크로 테마 분석
   │  (Claude Sonnet 4.6)     │  섹터 동향 · 수혜/위험 종목
   └──────────────┬───────────┘
                  │
                  ▼
   ┌──────────────────────────┐
   │       Notify Node        │  HTML 이메일 생성 · 발송
   │      (Gmail SMTP)        │
   └──────────────────────────┘
```

### 처리 흐름

**1단계 — 종목 발굴 (Discovery Node)**

| 신호 | 소스 | 가중치 |
|------|------|--------|
| 거래금액 순위 | Yahoo Finance Most Active | 40% |
| 펀더멘털 점수 | PEG(40%) + ROE(30%) + EPS성장(30%) | 30% |
| 뉴스 버즈 | Finnhub 종목별 뉴스 건수 | 20% |
| 시장 언급 빈도 | Finnhub 일반 시장 뉴스 | 10% |

- 시가총액 $500B 이하 종목만 대상 (config에서 조정 가능)
- 4개 신호를 정규화 후 가중 합산 → 상위 5종목 선정

**2단계 — AI 분석 (Report Single Node × 병렬)**

LangChain Tool-calling 에이전트가 종목별로 병렬 실행됩니다.

1. Claude가 필요한 도구를 스스로 판단해 호출 (`stock_data_tool`, `company_news_tool`)
2. 수집된 데이터를 바탕으로 3개 섹션 브리핑 생성
   - `[주목이유]` — 이번 주 왜 주목받고 있는지
   - `[핵심뉴스]` — 가장 중요한 뉴스 이슈
   - `[리스크]` — 투자 시 주의할 점

**3단계 — 테마 분석 (Theme Node)**

전 종목 데이터를 종합해 Claude가 주간 매크로 테마를 도출합니다.
- 이번 주 시장을 관통하는 핵심 투자 테마
- 수혜 섹터 / 위험 섹터
- 주목할 종목 추천 이유

**4단계 — 발송 (Notify Node)**

전 종목 리포트 + 테마 분석을 HTML 이메일로 조합 후 Gmail 발송

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 모델 | Claude Sonnet 4.6 (Anthropic) |
| LLM 프레임워크 | LangChain (`langchain_anthropic`, `@tool`) |
| AI 오케스트레이션 | LangGraph (StateGraph, Send API) |
| RAG | ChromaDB + sentence-transformers (SEC 10-Q 공시) |
| 종목 발굴 | Yahoo Finance, Finnhub |
| 주가/재무 데이터 | yfinance |
| 뉴스 데이터 | Finnhub API |
| 자동화 | GitHub Actions |
| 알림 | Gmail SMTP |
| 언어 | Python 3.11 |

---

## 프로젝트 구조

```
stock-briefing/
├── .github/workflows/
│   └── daily_report.yml        # GitHub Actions 스케줄러 (매주 토요일 10:00 KST)
├── graph/
│   ├── state.py                # LangGraph 상태 정의 (BriefingState)
│   ├── workflow.py             # 그래프 빌드 (노드 연결)
│   └── nodes/
│       ├── discovery.py        # 종목 자동 발굴 (멀티 신호 가중 합산)
│       ├── rag.py              # SEC 10-Q 수집 및 ChromaDB 벡터 저장
│       ├── report.py           # LangChain Tool-calling 분석 에이전트
│       ├── theme.py            # 매크로 테마 분석
│       └── notify.py           # 이메일 발송
├── tools/
│   ├── langchain_tools.py      # LangChain @tool 래퍼 (Claude 도구 호출용)
│   ├── rag_tool.py             # SEC EDGAR 10-Q 수집 + ChromaDB 벡터 저장/검색
│   ├── volume_tool.py          # Yahoo Finance 거래금액 상위 종목
│   ├── trends_tool.py          # Finnhub 뉴스 버즈 점수
│   ├── fundamental_tool.py     # PEG/ROE/EPS 펀더멘털 점수
│   ├── stock_tool.py           # yfinance 주가/재무 데이터
│   └── news_tool.py            # Finnhub 뉴스 수집 + 언급 카운팅
├── notifier/
│   └── email.py                # Gmail HTML 이메일 발송
├── config.py                   # TOP_N, MAX_MARKET_CAP 등 설정
├── main.py                     # 진입점
└── requirements.txt
```

---

## 시작하기

### 1. 의존성 설치

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 아래 값을 입력합니다:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
FINNHUB_API_KEY=your_finnhub_api_key
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
RECIPIENT_EMAIL=recipient@gmail.com
```

> Gmail 앱 비밀번호: Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호에서 발급

### 3. 로컬 테스트

```bash
python main.py
```

실행 시 콘솔에서 진행 상황을 확인할 수 있습니다:

```
[ Discovery Node ] 거래금액 상위 종목 수집 중...
[ Discovery Node ] 펀더멘털 점수 수집 중...
[ Discovery Node ] 뉴스 버즈 수집 중...
[ Discovery Node ] 시장 뉴스 언급 빈도 수집 중...

[ Discovery Node ] 선정 완료: PLTR, NVDA, TSLA, META, AMD
  PLTR: 종합 88.3 (거래금액 100 / 펀더멘털 72 / 버즈 85 / 언급 60)
  NVDA: 종합 81.2 (거래금액 95 / 펀더멘털 100 / 버즈 40 / 언급 50)
  ...

  [ Report Node ] PLTR 분석 중 (Tool-calling Agent)...
    ↳ Tool 호출: stock_data_tool({'ticker': 'PLTR'})
    ↳ Tool 호출: company_news_tool({'ticker': 'PLTR'})
  [ Report Node ] NVDA 분석 중 (Tool-calling Agent)...
  ...
```

### 4. GitHub Actions 설정

GitHub 레포지토리 → Settings → Secrets and variables → Actions에서 아래 5개를 등록합니다:

| Secret | 값 |
|--------|----|
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `FINNHUB_API_KEY` | Finnhub API 키 |
| `GMAIL_ADDRESS` | Gmail 주소 |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 |
| `RECIPIENT_EMAIL` | 수신 이메일 |

이후 매주 토요일 오전 10시(KST)에 자동 실행됩니다.

수동 실행: Actions 탭 → `Weekly Stock Briefing` → `Run workflow`

---

## 설정 변경

[config.py](config.py)에서 주요 파라미터를 조정할 수 있습니다:

```python
TOP_N = 5                           # 최종 분석할 종목 수 (늘릴수록 API 비용 증가)
MAX_MARKET_CAP = 500_000_000_000    # 시총 상한선 — $500B 이하 종목만 선정
REPORT_LANGUAGE = "Korean"          # 리포트 언어
```

---

## 주의사항

본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.
