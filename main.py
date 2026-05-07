from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI

from graph.workflow import build_graph


def run_briefing() -> dict:
    graph = build_graph()
    return graph.invoke({
        "tickers": [],
        "scores": {},
        "report_items": [],
        "theme": {},
    })


app = FastAPI(title="Stock Briefing")


@app.post("/run")
def trigger():
    print("=== Stock Briefing 시작 (HTTP) ===\n")
    result = run_briefing()
    print("\n=== 완료 ===")
    return {
        "report_items": result["report_items"],
        "theme": result["theme"],
    }


def main():
    print("=== Stock Briefing 시작 ===\n")
    run_briefing()
    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
