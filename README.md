# 📈 Stock Briefing

매주 토요일 오전 10시, AI가 이번 주 가장 주목받은 미국주식을 자동으로 선정하고 투자 브리핑을 이메일로 발송하는 에이전트입니다.

---

## 주요 기능

- **AI 종목 자동 발굴** — 거래량·Google Trends·뉴스 언급 빈도를 종합해 이번 주 TOP 5 종목 자동 선정
- **AI 분석 리포트** — Claude(Anthropic)가 주가 데이터와 뉴스를 종합해 종목별 투자 브리핑 생성
- **자동 데이터 수집** — yfinance(주가/재무), Finnhub(뉴스), Google Trends(검색량) 멀티소스 수집
- **이메일 자동 발송** — 매주 토요일 오전 10시 Gmail로 HTML 리포트 발송
- **무서버 운영** — GitHub Actions 기반, 별도 서버 없이 완전 자동화

---

## AI Workflow 아키텍처

```
[GitHub Actions — 매주 토요일 10:00 KST]
              │
              ▼
        ┌─────────────┐
        │   main.py   │  진입점
        └──────┬──────┘
               │
               ▼
   ┌───────────────────────────┐
   │     Discovery Agent       │  종목 자동 발굴
   │  (agents/discovery_agent) │
   └──────────┬────────────────┘
              │
       ┌──────┼──────┐
       │      │      │
       ▼      ▼      ▼
  ┌────────┐ ┌──────────────┐ ┌────────────┐
  │ Volume │ │Google Trends │ │ News Count │  데이터 수집
  │  Tool  │ │    Tool      │ │    Tool    │
  │(Yahoo) │ │ (pytrends)   │ │ (Finnhub)  │
  └────────┘ └──────────────┘ └────────────┘
       │      │      │
       └──────┼──────┘
              │  가중 합산 → TOP 5 선정
              │  (거래량 50% + 트렌드 30% + 뉴스 20%)
              ▼
   ┌───────────────────────┐
   │     Report Agent      │  AI 분석 오케스트레이터
   │  (agents/report_agent)│
   └──────────┬────────────┘
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
 ┌───────────┐  ┌───────────┐
 │ Stock Tool│  │ News Tool │  상세 데이터 수집
 │ (yfinance)│  │ (Finnhub) │
 └───────────┘  └───────────┘
       │             │
       └──────┬──────┘
              │
              ▼
   ┌─────────────────────┐
   │   Claude Sonnet     │  LLM 분석
   │  (Anthropic API)    │  — 뉴스 감성 분석
   └──────────┬──────────┘  — 주가 흐름 해석
              │              — 투자 브리핑 생성
              ▼
   ┌─────────────────────┐
   │   Email Notifier    │  결과 발송
   │   (Gmail SMTP)      │
   └─────────────────────┘
```

### 처리 흐름

**1단계 — 종목 발굴 (Discovery Agent)**

| 신호 | 소스 | 가중치 |
|------|------|--------|
| 거래량 순위 | Yahoo Finance Most Active | 50% |
| Google 검색량 | pytrends (Google Trends) | 30% |
| 뉴스 언급 빈도 | Finnhub 시장 뉴스 | 20% |

3개 신호를 정규화 후 가중 합산 → 상위 5종목 선정

**2단계 — AI 분석 (Report Agent)**

선정된 종목별로:
1. yfinance로 현재가·등락률·PER·52주 고저가 수집
2. Finnhub으로 최근 뉴스 헤드라인 5건 수집
3. Claude가 데이터를 종합해 3~5문장 투자 브리핑 생성

**3단계 — 발송**

전 종목 리포트를 HTML 이메일로 조합 후 Gmail 발송

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 모델 | Claude Sonnet (Anthropic) |
| 종목 발굴 | Yahoo Finance, pytrends, Finnhub |
| 주가 데이터 | yfinance |
| 뉴스 데이터 | Finnhub API |
| 자동화 | GitHub Actions |
| 알림 | Gmail SMTP |
| 언어 | Python 3.11 |

---

## 프로젝트 구조

```
stock-briefing/
├── .github/workflows/
│   └── daily_report.yml      # GitHub Actions 스케줄러 (매주 토요일 10:00 KST)
├── agents/
│   ├── discovery_agent.py    # 종목 자동 발굴 (멀티 신호 가중 합산)
│   └── report_agent.py       # AI 분석 오케스트레이터
├── tools/
│   ├── volume_tool.py        # Yahoo Finance 거래량 상위 종목
│   ├── trends_tool.py        # Google Trends 검색량
│   ├── stock_tool.py         # yfinance 주가/재무 데이터
│   └── news_tool.py          # Finnhub 뉴스 수집 + 언급 카운팅
├── notifier/
│   └── email.py              # Gmail 이메일 발송
├── config.py                 # TOP_N 등 설정
├── main.py                   # 진입점
└── requirements.txt
```

---

## 시작하기

### 1. 의존성 설치

```bash
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

실행 시 콘솔에서 종목 선정 점수를 확인할 수 있습니다:

```
[ Discovery ] 이번 주 주목 종목 선정 중...
[ 1/3 ] 거래량 상위 종목 수집 중...
[ 2/3 ] Google Trends 점수 수집 중...
[ 3/3 ] 뉴스 언급 빈도 수집 중...

이번 주 선정 종목: NVDA, TSLA, AAPL, META, AMD
  NVDA: 종합점수 91.2 (거래량 100 / 트렌드 87 / 뉴스 60)
  TSLA: 종합점수 78.4 (거래량 90 / 트렌드 72 / 뉴스 40)
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

[config.py](config.py)에서 분석 종목 수를 조정할 수 있습니다:

```python
TOP_N = 5  # 최종 분석할 종목 수 (늘릴수록 API 비용 증가)
```

---

## 리포트 예시

```
📈 미국주식 주간 브리핑 — 2026-05-04

이번 주 선정 종목: NVDA, TSLA, AAPL, META, AMD
선정 기준: 거래량 · Google 검색량 · 뉴스 언급 빈도 종합

### NVIDIA (NVDA)
$875.40 (+3.2%)

이번 주 NVIDIA는 데이터센터 수요 확대 기대감에 강한 상승세를 보였습니다.
블랙웰 GPU 출하량 증가 소식이 주가를 견인했으며, 애널리스트들의 목표주가
상향 조정이 이어졌습니다. 단기 과열 우려도 있으나 AI 인프라 수요는
지속될 것으로 전망됩니다.

---
...
```

---

## 주의사항

본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.
