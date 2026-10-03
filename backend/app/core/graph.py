"""LangGraph 编排 —— 把 4 个自动化 Agent 组装成一条流水线（含异常处理）。

这是整个系统的「装配车间」：把 4 个 Agent（节点）按顺序串起来，让 RiskState 在
节点间流动。第 5 个「人工复核」是交互式模块（agents/human_review.py），不走流水线。

异常处理：每个节点用 _safe 包装捕获异常，出错时写 status=error + error 信息，
通过条件路由直接跳到 END（下游节点不再执行），流水线不会整体崩溃。

流水线：文档解析 → 实体抽取 → 风险识别 → 报告生成（产出初审报告）
"""

from langgraph.graph import END, START, StateGraph

from app.core.state import STATUS_ERROR, RiskState, create_initial_state

from app.agents.doc_parser import parse_document
from app.agents.entity_extractor import extract_entities
from app.agents.report_generator import generate_report
from app.agents.risk_identifier import identify_risks


def _safe(node_fn, node_name: str):
    """包装节点函数：捕获任何异常，写入 status=error + error 信息，避免流水线崩溃。"""
    def wrapper(state: RiskState) -> dict:
        try:
            return node_fn(state)
        except Exception as e:
            return {"status": STATUS_ERROR, "error": f"[{node_name}] {type(e).__name__}: {e}"}
    return wrapper


def _should_continue(state: RiskState) -> str:
    """条件路由：有错误则跳到 END（停止），否则继续下一个节点。"""
    return "error" if state.get("error") else "continue"


def build_graph():
    """构建并编译 LangGraph 流水线（4 个自动化 Agent + 异常处理）。"""
    g = StateGraph(RiskState)

    g.add_node("doc_parser", _safe(parse_document, "doc_parser"))
    g.add_node("entity_extractor", _safe(extract_entities, "entity_extractor"))
    g.add_node("risk_identifier", _safe(identify_risks, "risk_identifier"))
    g.add_node("report_generator", _safe(generate_report, "report_generator"))

    g.add_edge(START, "doc_parser")
    g.add_conditional_edges("doc_parser", _should_continue, {"error": END, "continue": "entity_extractor"})
    g.add_conditional_edges("entity_extractor", _should_continue, {"error": END, "continue": "risk_identifier"})
    g.add_conditional_edges("risk_identifier", _should_continue, {"error": END, "continue": "report_generator"})
    g.add_edge("report_generator", END)

    return g.compile()


def run_pipeline(task_id: str, file_path: str, file_name: str = "") -> RiskState:
    """便捷入口：构建图 → 造初始状态 → 跑一遍 → 返回最终状态（初审报告或错误状态）。"""
    app = build_graph()
    initial = create_initial_state(task_id, file_path, file_name)
    return app.invoke(initial)
