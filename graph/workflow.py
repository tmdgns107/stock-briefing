from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from graph.state import BriefingState
from graph.nodes.discovery import discovery_node
from graph.nodes.rag import rag_node
from graph.nodes.report import dispatch_reports, report_single
from graph.nodes.theme import theme_node
from graph.nodes.notify import notify_node


def build_graph():
    graph = StateGraph(BriefingState)

    graph.add_node("discovery", discovery_node)
    graph.add_node("rag", rag_node)
    graph.add_node("report_single", report_single)
    graph.add_node("theme", theme_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "discovery")
    graph.add_edge("discovery", "rag")

    # rag 완료 후 종목별 report_single 병렬 분배
    graph.add_conditional_edges("rag", dispatch_reports, ["report_single"])

    # 모든 report_single 완료 후 theme으로 합류
    graph.add_edge("report_single", "theme")

    graph.add_edge("theme", "notify")
    graph.add_edge("notify", END)

    return graph.compile()
