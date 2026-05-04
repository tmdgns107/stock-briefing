# 📈 Stock Briefing

매주 토요일 오전 10시, AI가 미국주식 주간 브리핑을 이메일로 자동 발송하는 에이전트입니다.

---

## 주요 기능

- **AI 분석 리포트** — Claude(Anthropic)가 주가 데이터와 뉴스를 종합해 종목별 투자 브리핑 생성
- **자동 데이터 수집** — yfinance(주가/재무), Finnhub(뉴스)에서 실시간 데이터 수집
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
   ┌───────────────────────┐
   │     Report Agent      │  AI 분석 오케스트레이터
   │  (agents/report_agent)│
   └──────────┬────────────┘
              │
       ┌──────┴──────┐
       │             │
       ▼             ▼
 ┌───────────┐  ┌───────────┐
 │ Stock Tool│  │ News Tool │  데이터 수집 레이어
 │ (yfinance)│  │ (Finnhub) │
 └───────────┘  └───────────┘
       │             │
       └──────┬──────┘
              │  종목별 데이터 통합
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

### 처리 흐름 (종목당)

1. **데이터 수집** — yfinance로 현재가·등락률·PER·52주 고저가 수집
2. **뉴스 수집** — Finnhub API로 최근 뉴스 헤드라인 5건 수집
3. **프롬프트 생성** — 수집 데이터를 구조화된 프롬프트로 변환
4. **AI 분석** — Claude가 데이터를 종합해 3~5문장 투자 브리핑 생성
5. **리포트 통합** — 전 종목 분석 결과를 하나의 HTML 이메일로 조합
6. **발송** — Gmail SMTP로 수신자에게 전달

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| AI 모델 | Claude Sonnet (Anthropic) |
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
│   └── daily_report.yml    # GitHub Actions 스케줄러
├── agents/
│   └── report_agent.py     # AI 분석 오케스트레이터
├── tools/
│   ├── stock_tool.py       # yfinance 주가 데이터 수집
│   └── news_tool.py        # Finnhub 뉴스 수집
├── notifier/
│   └── email.py            # Gmail 이메일 발송
├── config.py               # 관심 종목 설정
├── main.py                 # 진입점
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

### 4. GitHub Actions 설정

GitHub 레포지토리 → Settings → Secrets and variables → Actions에서 위 환경 변수를 모두 등록합니다.

이후 매주 토요일 오전 10시(KST)에 자동 실행됩니다.

수동 실행은 Actions 탭 → `Weekly Stock Briefing` → `Run workflow`로 가능합니다.

---

## 관심 종목 변경

[config.py](config.py)에서 종목 리스트를 수정합니다:

```python
WATCHLIST = [
    "AAPL",   # Apple
    "NVDA",   # NVIDIA
    "MSFT",   # Microsoft
    "TSLA",   # Tesla
    "AMZN",   # Amazon
]
```

---

## 리포트 예시

```
📈 미국주식 주간 브리핑 — 2026-05-04

### NVIDIA (NVDA)
$875.40 (+3.2%)

이번 주 NVIDIA는 데이터센터 수요 확대 기대감에 강한 상승세를 보였습니다.
블랙웰 GPU 출하량 증가 소식이 주가를 견인했으며, 애널리스트들의 목표주가
상향 조정이 이어졌습니다. 단기 과열 우려도 있으나 AI 인프라 수요는
지속될 것으로 전망됩니다.

---

### Apple (AAPL)
$189.20 (-0.8%)
...
```

---

## 주의사항

본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.
