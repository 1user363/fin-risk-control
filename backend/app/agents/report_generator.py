"""标准化报告生成 Agent（流水线第 4 步）。

职责：汇总实体、风险点、合规建议，生成标准化审查报告。
输入：RiskState 全部字段（entities / risks / task_id / file_name）
输出：写入 RiskState.report（Report 模型）
依赖：templates/report.md.j2（Jinja2 模板，供 render_report_markdown 渲染）
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.state import STATUS_REPORTING, RiskState
from app.models import Report, RiskLevel

# Jinja2 模板目录：backend/templates（本文件在 backend/app/agents/，上三级是 backend）
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _decide_conclusion(risks: list) -> str:
    """根据风险点定初审结论：
    - 无风险 → 通过
    - 有高风险 → 不通过
    - 只有中/低风险 → 需人工复核
    """
    if not risks:
        return "通过"
    if any(r.risk_level == RiskLevel.HIGH for r in risks):
        return "不通过"
    return "需人工复核"


def _summarize(risks: list) -> str:
    """生成风险汇总段落（规则版，不调 LLM，确定性输出）。"""
    if not risks:
        return "未识别到合规风险。"
    high = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)
    medium = sum(1 for r in risks if r.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for r in risks if r.risk_level == RiskLevel.LOW)
    types = {r.risk_type.value for r in risks}
    return f"共识别 {len(risks)} 个风险点（高 {high} / 中 {medium} / 低 {low}），涉及：{'、'.join(types)}。"


def build_report(task_id: str, file_name: str, entities, risks: list) -> Report:
    """根据输入构建 Report（供报告生成 Agent 与人工复核共用）。"""
    return Report(
        task_id=task_id,
        file_name=file_name,
        conclusion=_decide_conclusion(risks),
        entities=entities,
        risks=risks,
        risk_summary=_summarize(risks),
        suggestions=[r.suggestion for r in risks],
    )


def generate_report(state: RiskState) -> dict:
    """节点④：汇总实体、风险点，生成标准化审查报告。"""
    report = build_report(
        state["task_id"],
        state["file_name"],
        state.get("entities"),
        state.get("risks") or [],
    )
    return {"report": report, "status": STATUS_REPORTING}


def render_report_markdown(report: Report) -> str:
    """用 Jinja2 模板把报告渲染成 Markdown（供预览/导出）。"""
    template = _env.get_template("report.md.j2")
    return template.render(report=report)
