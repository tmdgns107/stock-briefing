import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _score_bar(score: float, total: int = 5) -> str:
    filled = round(score / 100 * total)
    return "●" * filled + "○" * (total - filled)


def _fmt(value, prefix="", suffix="", decimals=2):
    if value is None or value == "N/A":
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{prefix}{value:.{decimals}f}{suffix}"
    return str(value)


def _stock_card(item: dict) -> str:
    if item.get("error"):
        return f"""
<div style="border:1px solid #ddd; border-radius:8px; padding:20px; margin-bottom:20px;">
  <h3 style="color:#999;">{item['ticker']} — 데이터 수집 실패</h3>
</div>"""

    s = item["stock"]
    a = item["analysis"]
    sc = item["scores"]
    change = s["weekly_change_pct"]
    change_color = "#e53e3e" if change < 0 else "#276749"
    change_sign = "▲" if change >= 0 else "▼"

    pe = _fmt(s.get("pe_ratio"), decimals=1)
    fpe = _fmt(s.get("forward_pe"), decimals=1)
    eps = _fmt(s.get("eps"), "$", decimals=2)
    high = _fmt(s.get("52w_high"), "$", decimals=2)
    low = _fmt(s.get("52w_low"), "$", decimals=2)
    target = _fmt(s.get("target_price"), "$", decimals=2)

    return f"""
<div style="border:1px solid #e2e8f0; border-radius:10px; padding:24px; margin-bottom:24px; background:#fff;">

  <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px;">
    <div>
      <span style="font-size:18px; font-weight:700; color:#1a202c;">{s['name']}</span>
      <span style="font-size:15px; color:#718096; margin-left:6px;">({s['ticker']})</span>
      <span style="display:inline-block; margin-left:10px; padding:2px 10px; background:#ebf4ff; color:#2b6cb0; border-radius:20px; font-size:12px;">{s.get('sector','N/A')}</span>
    </div>
    <div style="text-align:right;">
      <div style="font-size:22px; font-weight:700; color:#1a202c;">${s['price']}</div>
      <div style="font-size:14px; color:{change_color}; font-weight:600;">{change_sign} {abs(change):.2f}% (주간)</div>
    </div>
  </div>

  <table style="width:100%; border-collapse:collapse; font-size:13px; margin-bottom:16px;">
    <tr style="background:#f7fafc;">
      <td style="padding:8px 12px; color:#718096;">시가총액</td>
      <td style="padding:8px 12px; font-weight:600;">{s['market_cap']}</td>
      <td style="padding:8px 12px; color:#718096;">PER</td>
      <td style="padding:8px 12px; font-weight:600;">{pe}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px; color:#718096;">Forward PER</td>
      <td style="padding:8px 12px; font-weight:600;">{fpe}</td>
      <td style="padding:8px 12px; color:#718096;">EPS</td>
      <td style="padding:8px 12px; font-weight:600;">{eps}</td>
    </tr>
    <tr style="background:#f7fafc;">
      <td style="padding:8px 12px; color:#718096;">52주 고가</td>
      <td style="padding:8px 12px; font-weight:600;">{high}</td>
      <td style="padding:8px 12px; color:#718096;">52주 저가</td>
      <td style="padding:8px 12px; font-weight:600;">{low}</td>
    </tr>
    <tr>
      <td style="padding:8px 12px; color:#718096;">목표주가</td>
      <td style="padding:8px 12px; font-weight:600;" colspan="3">{target}</td>
    </tr>
  </table>

  <div style="background:#f0f4f8; border-radius:6px; padding:10px 14px; font-size:12px; color:#4a5568; margin-bottom:16px;">
    <span style="font-weight:600;">선정 점수</span>&nbsp;&nbsp;
    거래금액 {_score_bar(sc.get('volume', 0))}&nbsp;
    펀더멘털 {_score_bar(sc.get('fundamental', 0))}&nbsp;
    뉴스버즈 {_score_bar(sc.get('buzz', 0))}&nbsp;
    언급 {_score_bar(sc.get('mention', 0))}
    <span style="float:right; font-weight:700; color:#2b6cb0;">종합 {sc.get('total', 0):.0f}점</span>
  </div>

  <div style="border-left:3px solid #4299e1; padding-left:14px; margin-bottom:10px;">
    <div style="font-size:12px; color:#2b6cb0; font-weight:700; margin-bottom:4px;">📌 주목 이유</div>
    <div style="font-size:13px; color:#2d3748; line-height:1.6;">{a.get('주목이유', 'N/A')}</div>
  </div>

  <div style="border-left:3px solid #68d391; padding-left:14px; margin-bottom:10px;">
    <div style="font-size:12px; color:#276749; font-weight:700; margin-bottom:4px;">📰 핵심 뉴스</div>
    <div style="font-size:13px; color:#2d3748; line-height:1.6;">{a.get('핵심뉴스', 'N/A')}</div>
  </div>

  <div style="border-left:3px solid #fc8181; padding-left:14px;">
    <div style="font-size:12px; color:#c53030; font-weight:700; margin-bottom:4px;">⚠️ 리스크</div>
    <div style="font-size:13px; color:#2d3748; line-height:1.6;">{a.get('리스크', 'N/A')}</div>
  </div>

</div>"""


def _theme_section(theme: dict) -> str:
    beneficiaries = "".join([
        f"""<div style="margin-bottom:10px;">
          <span style="display:inline-block; background:#c6f6d5; color:#276749; border-radius:4px; padding:2px 8px; font-size:12px; font-weight:700;">✅ {b['sector']}</span>
          <span style="font-size:13px; color:#2d3748; margin-left:8px;">{b['reason']}</span>
          <div style="font-size:12px; color:#718096; margin-top:3px; margin-left:4px;">관련 종목: {' · '.join(b.get('examples', []))}</div>
        </div>"""
        for b in theme.get("beneficiary_sectors", [])
    ])

    risks = "".join([
        f"""<div style="margin-bottom:8px;">
          <span style="display:inline-block; background:#fed7d7; color:#c53030; border-radius:4px; padding:2px 8px; font-size:12px; font-weight:700;">⚠️ {r['sector']}</span>
          <span style="font-size:13px; color:#2d3748; margin-left:8px;">{r['reason']}</span>
        </div>"""
        for r in theme.get("risk_sectors", [])
    ])

    watches = "".join([
        f"""<div style="display:inline-block; background:#ebf8ff; border:1px solid #bee3f8; border-radius:6px; padding:8px 14px; margin:4px;">
          <div style="font-size:13px; font-weight:700; color:#2b6cb0;">{w['ticker']}</div>
          <div style="font-size:11px; color:#4a5568;">{w['name']}</div>
          <div style="font-size:12px; color:#2d3748; margin-top:4px;">{w['reason']}</div>
        </div>"""
        for w in theme.get("watch_stocks", [])
    ])

    return f"""
<div style="border:1px solid #e2e8f0; border-radius:10px; padding:24px; margin-bottom:24px; background:#fff;">
  <div style="font-size:16px; font-weight:700; color:#1a202c; margin-bottom:4px;">
    🌐 이번 주 매크로 테마 &nbsp;
    <span style="display:inline-block; background:#ebf4ff; color:#2b6cb0; border-radius:20px; padding:2px 12px; font-size:13px; font-weight:600;">{theme.get('theme_title','')}</span>
  </div>
  <p style="font-size:13px; color:#4a5568; line-height:1.7; margin:12px 0 18px;">{theme.get('theme_summary','')}</p>

  <div style="margin-bottom:16px;">
    <div style="font-size:12px; font-weight:700; color:#718096; margin-bottom:10px; letter-spacing:0.05em;">수혜 섹터</div>
    {beneficiaries}
  </div>

  <div style="margin-bottom:16px;">
    <div style="font-size:12px; font-weight:700; color:#718096; margin-bottom:10px; letter-spacing:0.05em;">주의 섹터</div>
    {risks}
  </div>

  <div>
    <div style="font-size:12px; font-weight:700; color:#718096; margin-bottom:10px; letter-spacing:0.05em;">함께 볼 종목</div>
    <div>{watches}</div>
  </div>
</div>"""


def send_email(report_items: list[dict], theme: dict | None = None):
    sender = os.environ["GMAIL_ADDRESS"]
    password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["RECIPIENT_EMAIL"]
    today = date.today().strftime("%Y년 %m월 %d일")

    tickers = [i["ticker"] for i in report_items if not i.get("error")]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[Stock Briefing] {date.today().strftime('%Y-%m-%d')} 미국주식 주간 브리핑"
    msg["From"] = sender
    msg["To"] = recipient

    cards = "".join(_stock_card(item) for item in report_items)
    theme_html = _theme_section(theme) if theme else ""

    html = f"""
<html>
<body style="background:#f0f4f8; font-family:'Helvetica Neue',Arial,sans-serif; padding:20px;">
<div style="max-width:680px; margin:auto;">

  <div style="background:linear-gradient(135deg,#1a365d,#2b6cb0); border-radius:12px; padding:28px 32px; margin-bottom:24px; color:#fff;">
    <div style="font-size:22px; font-weight:700; margin-bottom:6px;">📈 미국주식 주간 브리핑</div>
    <div style="font-size:14px; opacity:0.85;">{today}</div>
    <div style="margin-top:14px; font-size:13px; opacity:0.8;">
      이번 주 선정 종목: <strong>{' · '.join(tickers)}</strong>
    </div>
    <div style="margin-top:6px; font-size:12px; opacity:0.7;">
      선정 기준: 거래금액 40% + 펀더멘털(PEG·ROE·EPS) 30% + 뉴스버즈 20% + 언급 10%
    </div>
  </div>

  {theme_html}

  {cards}

  <div style="text-align:center; font-size:11px; color:#a0aec0; padding:16px 0;">
    본 리포트는 투자 권유가 아닙니다. 참고용으로만 활용하세요.
  </div>

</div>
</body>
</html>"""

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"이메일 발송 완료 → {recipient}")
