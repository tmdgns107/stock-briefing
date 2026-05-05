from dotenv import load_dotenv
load_dotenv(override=True)

from graph.workflow import build_graph


def main():
    print("=== Stock Briefing 시작 ===\n")

    app = build_graph()
    app.invoke({
        "tickers": [],
        "scores": {},
        "report_items": [],
        "theme": {},
    })

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
