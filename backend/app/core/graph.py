"""LangGraph 编排 —— 把 4 个自动化 Agent 组装成一条流水线。

这是整个系统的「装配车间」：它本身不做任何业务，只负责把 4 个 Agent（节点）
按顺序串起来，让 RiskState 在节点间流动。第 5 个「人工复核」是交互式模块
（agents/human_review.py），不走流水线，由 API 在流水线跑完后触发。

核心三要素：
  1. StateGraph(RiskState) —— 以 RiskState 为「工件」的图
  2. add_node(名字, 函数)   —— 注册节点（一个 Agent = 一个节点）
  3. add_edge(谁, 谁)       —— 定义执行顺序（任务依赖关系）

流水线：文档解析 → 实体抽取 → 风险识别 → 报告生成（产出初审报告）
"""

from langgraph.graph import END, START, StateGraph

from app.core.state import RiskState, create_initial_state

from app.agents.doc_parser import parse_document
from app.agents.entity_extractor import extract_entities
from app.agents.report_generator import generate_report
from app.agents.risk_identifier import identify_risks


def build_graph():
    """构建并编译 LangGraph 流水线（4 个自动化 Agent）。"""
    g = StateGraph(RiskState)

    g.add_node("doc_parser", parse_document)
    g.add_node("entity_extractor", extract_entities)
    g.add_node("risk_identifier", identify_risks)
    g.add_node("report_generator", generate_report)

    # 用边定义执行顺序：START/END 是 LangGraph 内置的起点/终点
    g.add_edge(START, "doc_parser")
    g.add_edge("doc_parser", "entity_extractor")
    g.add_edge("entity_extractor", "risk_identifier")
    g.add_edge("risk_identifier", "report_generator")
    g.add_edge("report_generator", END)

    return g.compile()


def run_pipeline(task_id: str, file_path: str, file_name: str = "") -> RiskState:
    """便捷入口：构建图 → 造初始状态 → 跑一遍 → 返回最终状态（初审报告）。"""
    app = build_graph()
    initial = create_initial_state(task_id, file_path, file_name)
    return app.invoke(initial)
