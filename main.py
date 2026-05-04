from dotenv import load_dotenv
load_dotenv()

from agents.discovery_agent import discover_tickers
from agents.report_agent import generate_report
from agents.theme_agent import analyze_theme
from notifier.email import send_email


def main():
    print("=== Stock Briefing 시작 ===\n")

    print("[ Discovery ] 이번 주 주목 종목 선정 중...")
    tickers, scores = discover_tickers()

    print("\n[ Report ] AI 종목별 분석 중...")
    report_items = generate_report(tickers, scores)

    print("\n[ Theme ] 매크로 테마 분석 중...")
    theme = analyze_theme(report_items)
    print(f"  → 테마: {theme.get('theme_title')}")

    print("\n[ Notify ] 이메일 발송 중...")
    send_email(report_items, theme)

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
