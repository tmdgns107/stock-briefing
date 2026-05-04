from dotenv import load_dotenv
load_dotenv()

from agents.discovery_agent import discover_tickers
from agents.report_agent import generate_report
from notifier.email import send_email


def main():
    print("=== Stock Briefing 시작 ===\n")

    print("[ Discovery ] 이번 주 주목 종목 선정 중...")
    tickers = discover_tickers()

    print("\n[ Report ] AI 분석 리포트 생성 중...")
    report = generate_report(tickers)
    print(report)

    print("\n[ Notify ] 이메일 발송 중...")
    send_email(report)

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
