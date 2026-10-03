"""人工复核 Agent（第 5 步，人机协同闭环）。

注意：本 Agent 是「交互式」的，不走自动流水线（流水线到 ④ 报告生成为止）。
由 API 接收风控人员的复核动作，调用 apply_review 应用修正并生成终审报告。

职责：
- 对风险点 确认(confirm) / 修改(modify) / 新增(add) / 驳回(revoke)
- 记录复核日志（谁 / 何时 / 改了什么 / 改前→改后）
- 生成终审报告 final_report
"""

from datetime import datetime

from app.agents.report_generator import build_report
from app.core.state import STATUS_DONE, RiskState
from app.models import ReviewAction, RiskLevel, RiskType


def _convert(risk, field_name: str, new_value: str):
    """把字符串 new_value 转成目标字段的类型（枚举需要转换）。"""
    if field_name == "risk_level":
        return RiskLevel(new_value)  # "高" -> RiskLevel.HIGH
    if field_name == "risk_type":
        return RiskType(new_value)   # "保本承诺" -> RiskType.PRINCIPAL_GUARANTEE
    return new_value  # 字符串字段（description/suggestion 等）直接返回


def _to_str(v) -> str:
    """枚举取 .value（中文值），其他类型取 str。"""
    return v.value if isinstance(v, (RiskLevel, RiskType)) else str(v)


def _apply_one(action: ReviewAction, risks: list, reviewer: str, now: str) -> dict:
    """应用单个动作到风险列表，返回一条复核日志。"""
    if action.action == "confirm":
        risk = risks[action.risk_index]
        return {"action": "confirm", "risk_type": risk.risk_type.value,
                "reviewer": reviewer, "remark": action.remark, "time": now}

    if action.action == "modify":
        risk = risks[action.risk_index]
        old = getattr(risk, action.field_name)
        new = _convert(risk, action.field_name, action.new_value)
        setattr(risk, action.field_name, new)
        return {"action": "modify", "field_name": action.field_name,
                "old_value": _to_str(old), "new_value": _to_str(new),
                "reviewer": reviewer, "remark": action.remark, "time": now}

    if action.action == "revoke":
        risk = risks.pop(action.risk_index)
        return {"action": "revoke", "risk_type": risk.risk_type.value,
                "reviewer": reviewer, "remark": action.remark, "time": now}

    if action.action == "add":
        risks.append(action.new_risk)
        return {"action": "add", "risk_type": action.new_risk.risk_type.value,
                "reviewer": reviewer, "remark": action.remark, "time": now}

    return {}


def apply_review(state: RiskState, actions: list[ReviewAction], reviewer: str = "") -> dict:
    """应用一批复核动作，记录日志，生成终审报告。

    返回部分状态更新（risks / review_log / final_report / status）。
    """
    risks = list(state.get("risks") or [])
    review_log = list(state.get("review_log") or [])
    now = datetime.now().isoformat(timespec="seconds")

    for action in actions:
        log = _apply_one(action, risks, reviewer, now)
        if log:
            review_log.append(log)

    final_report = build_report(
        state["task_id"], state["file_name"], state.get("entities"), risks
    )
    return {
        "risks": risks,
        "review_log": review_log,
        "final_report": final_report,
        "status": STATUS_DONE,
    }
