# 📈 Stock Briefing

매주 토요일 오전 10시, AI가 이번 주 가장 주목받은 미국주식을 자동으로 선정하고 투자 브리핑을 이메일로 발송하는 에이전트입니다.

---

## 주요 기능

- **AI 종목 자동 발굴** — 거래대금·펀더멘털·뉴스 급증 3가지 신호를 종합해 TOP 5 선정, 섹터 편중 방지 적용
- **LangChain Tool-calling 분석** — Claude가 필요한 데이터를 스스로 판단해 도구를 호출하고 종목별 투자 브리핑 생성
- **RAG 기반 공시 분석** — SEC 실적 공시(10-Q / 외국기업 6-K·20-F)를 ChromaDB에 벡터 저장, Claude가 의미 기반 검색으로 공시 근거 활용
- **공시 근거 교차 검증** — 생성된 리포트의 리스크 주장이 실제 SEC 공시로 뒷받침되는지 Claude가 재판정 (할루시네이션 탐지)
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
                  │  후보 250개 → 시총 $2B~$500B 필터
                  │  3가지 신호 가중 합산 → TOP 5 선정
       ┌──────────┼──────────┐
       ▼          ▼          ▼
  ┌─────────┐ ┌────────┐ ┌───────┐
  │거래대금   │ │ 펀더멘털 │ │뉴스 급증│
  │(Yahoo)  │ │(PEG/ROE│ │평소 대비│
  │  45%    │ │ EPS)   │ │  20%  │
  │         │ │  35%   │ │  배수  │
  └─────────┘ └────────┘ └───────┘
                  │  섹터당 최대 2종목
                  │
                  ▼
   ┌──────────────────────────┐
   │        RAG Node          │  SEC 실적 공시 수집 · 벡터 저장
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
   │       Verify Node        │  공시 근거 교차 검증
   │    (Claude Opus 5)       │  리스크 주장 ↔ RAG 근거 대조
   └──────────────┬───────────┘  → supported / 근거 부족 판정
                  │
                  ▼
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
| 거래대금 | Yahoo Finance Most Active (log 스케일) | 45% |
| 펀더멘털 점수 | PEG(40%) + ROE(30%) + EPS성장(30%) | 35% |
| 뉴스 급증 배수 | 이번 주 뉴스량 ÷ 직전 4주 평균 (Finnhub) | 20% |

- 후보 250종목(Yahoo 최대치)을 받아 **시총 $2B ~ $500B** 구간만 대상 (config에서 조정 가능)
- 3개 신호를 **동일한 min-max 척도(0~100)** 로 정규화 후 가중 합산 → 상위 5종목 선정
- 펀더멘털 지표 결측 시 중립값이 아니라 **사전값(40) 쪽으로 수축**시켜 '데이터 없음'이 유리해지지 않도록 처리
- **섹터당 최대 2종목** 제약으로 편중 방지 (제약으로 자리가 남으면 점수순 보충)

**2단계 — AI 분석 (Report Single Node × 병렬)**

LangChain Tool-calling 에이전트가 종목별로 병렬 실행됩니다.

1. Claude가 필요한 도구를 스스로 판단해 호출 (`stock_data_tool`, `company_news_tool`, `sec_filing_tool`)
2. 수집된 데이터를 바탕으로 3개 섹션 브리핑 생성
   - `[주목이유]` — 이번 주 왜 주목받고 있는지
   - `[핵심뉴스]` — 가장 중요한 뉴스 이슈
   - `[리스크]` — 투자 시 주의할 점

**3단계 — 공시 근거 검증 (Verify Node)**

병렬 분석이 모두 끝난 뒤 한 번 실행되며, 각 종목의 `[리스크]` 주장을 검증합니다.

1. 주장 문장을 질의로 삼아 해당 종목의 공시 청크를 RAG로 재검색 (상위 8개)
2. Claude가 "주장이 공시 근거로 뒷받침되는가"를 판정
3. 결과를 Pydantic 스키마(구조화 출력)로 받아 `state["verifications"]`에 저장

판정은 세 가지로 갈립니다.

| 상태 | 의미 |
|------|------|
| ✅ 공시 근거 확인 | 공시가 주장을 뒷받침함 |
| ⚠️ 공시 근거 부족 | 공시에 관련 내용이 없거나 주장과 어긋남 |
| — 공시 대조 불가 | 실적 공시를 찾지 못해 판정 자체가 불가 |

'대조 불가'를 따로 둔 이유는, 공시가 없어 확인 못 한 것과 확인해 보니 근거가 없는 것이 전혀 다른 상황이기 때문입니다.

**4단계 — 테마 분석 (Theme Node)**

전 종목 데이터를 종합해 Claude가 주간 매크로 테마를 도출합니다.
- 이번 주 시장을 관통하는 핵심 투자 테마
- 수혜 섹터 / 위험 섹터
- 주목할 종목 추천 이유

**5단계 — 발송 (Notify Node)**

전 종목 리포트 + 테마 분석을 HTML 이메일로 조합 후 Gmail 발송

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 모델 | Claude Opus 5 (검증) / Claude Sonnet 4.6 (분석·테마) |
| LLM 프레임워크 | LangChain (`langchain_anthropic`, `@tool`) |
| AI 오케스트레이션 | LangGraph (StateGraph, Send API) |
| RAG | ChromaDB + sentence-transformers (SEC 10-Q / 6-K / 20-F) |
| 출력 검증 | Anthropic 구조화 출력 (`messages.parse` + Pydantic) |
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
│       ├── rag.py              # SEC 실적 공시 수집 및 ChromaDB 벡터 저장
│       ├── report.py           # LangChain Tool-calling 분석 에이전트
│       ├── verify.py           # 공시 근거 교차 검증 (LLM 판정)
│       ├── theme.py            # 매크로 테마 분석
│       └── notify.py           # 이메일 발송
├── tools/
│   ├── langchain_tools.py      # LangChain @tool 래퍼 (Claude 도구 호출용)
│   ├── rag_tool.py             # SEC EDGAR 공시 수집(10-Q→6-K→20-F) + 벡터 저장/검색
│   ├── finnhub_client.py       # Finnhub 공용 클라이언트 (레이트리밋·429 재시도)
│   ├── volume_tool.py          # Yahoo 스크리너 → 시총 필터 → 거래대금 정렬
│   ├── trends_tool.py          # 평소 대비 뉴스 급증 배수
│   ├── fundamental_tool.py     # PEG/ROE/EPS 펀더멘털 점수
│   ├── stock_tool.py           # yfinance 주가/재무 데이터
│   └── news_tool.py            # Finnhub 종목 뉴스 수집
├── notifier/
│   └── email.py                # Gmail HTML 이메일 발송
├── config.py                   # TOP_N, MAX_MARKET_CAP, LLM_MODEL 등 설정
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
[ Discovery Node ] 거래대금 상위 종목 수집 중...
  [Volume] 후보 250개 → 시총 필터 통과 232개 (상한 초과 18 / 하한 미달 0 / 데이터 없음 0)
[ Discovery Node ] 펀더멘털 점수 수집 중...
[ Discovery Node ] 뉴스 버즈 수집 중 (평소 대비 배수)...
  [Buzz] CRM: 1.65배 (이번주 135건 / 평소 81.8건) [135, 42, 81, 93, 111]
  섹터 제한으로 제외: SNDK(Technology), PLTR(Technology), ORCL(Technology)
  섹터 분포: Technology 2 / Communication Services 1 / Industrials 1 / Financial Services 1

[ Discovery Node ] 선정 완료: CRM, MRVL, NBIS, BE, HOOD
  CRM: 종합 82.4 (거래대금 65 / 펀더멘털 95 / 버즈 99) [Technology]
  MRVL: 종합 73.4 (거래대금 90 / 펀더멘털 55 / 버즈 68) [Technology]
  ...

  [ Report Node ] PLTR 분석 중 (Tool-calling Agent)...
    ↳ Tool 호출: stock_data_tool({'ticker': 'PLTR'})
    ↳ Tool 호출: company_news_tool({'ticker': 'PLTR'})
  [ Report Node ] NVDA 분석 중 (Tool-calling Agent)...
  ...

[ Verify Node ] 리포트 근거 검증 중...
  PLTR: 근거 확인 — 공시 위험요인에 매출 성장 지속 불확실성이 명시되어 주장을 뒷받침합니다.
  NVDA: 근거 부족 — 제시된 공시 근거에 해당 리스크를 뒷받침하는 내용이 없습니다.
  ...

[ Theme Node ] 매크로 테마 분석 중...
  → 테마: AI 인프라 강세

[ Notify Node ] 이메일 발송 중...
이메일 발송 완료 → recipient@gmail.com
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
LLM_MODEL = "claude-opus-5"         # Verify 노드가 사용하는 모델
```

> `report.py` / `theme.py`는 아직 `claude-sonnet-4-6`을 직접 지정합니다.
> 전체를 한 모델로 통일하려면 두 파일의 모델 문자열을 `LLM_MODEL` 참조로 바꾸면 됩니다.

---

## 주의사항

본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.
