"""报告生成 + 人工复核单元测试。"""

from app.agents.human_review import apply_review
from app.agents.report_generator import _decide_conclusion, build_report
from app.models import FinancialEntity, ReviewAction, RiskLevel, RiskPoint, RiskType


def _risk(level=RiskLevel.MEDIUM, rtype=RiskType.EXAGGERATED_RETURN):
    return RiskPoint(risk_type=rtype, risk_level=level, description="d", evidence="e", suggestion="s", engine="rule")


def test_conclusion_logic():
    assert _decide_conclusion([]) == "通过"
    assert _decide_conclusion([_risk(RiskLevel.HIGH)]) == "不通过"
    assert _decide_conclusion([_risk(RiskLevel.MEDIUM)]) == "需人工复核"
    assert _decide_conclusion([_risk(RiskLevel.LOW)]) == "需人工复核"


def test_build_report_suggestions():
    risks = [_risk()]
    report = build_report("T1", "a.pdf", None, risks)
    assert report.suggestions == ["s"]


def test_apply_review_modify():
    """复核修改等级：改前→改后记录进日志，等级更新。"""
    state = {"task_id": "T1", "file_name": "a.pdf", "entities": None,
             "risks": [_risk(RiskLevel.HIGH)], "review_log": None}
    result = apply_review(state, [ReviewAction(action="modify", risk_index=0, field_name="risk_level", new_value="中")], reviewer="张三")
    assert result["risks"][0].risk_level == RiskLevel.MEDIUM
    assert result["review_log"][0]["old_value"] == "高"
    assert result["review_log"][0]["new_value"] == "中"


def test_apply_review_revoke():
    """复核驳回：风险被移除，结论自动重算。"""
    state = {"task_id": "T1", "file_name": "a.pdf", "entities": None,
             "risks": [_risk(RiskLevel.HIGH)], "review_log": None}
    result = apply_review(state, [ReviewAction(action="revoke", risk_index=0)], reviewer="李四")
    assert result["risks"] == []
    assert result["final_report"].conclusion == "通过"  # 高风险被驳回后 → 通过


def test_apply_review_add():
    """复核新增风险。"""
    state = {"task_id": "T1", "file_name": "a.pdf", "entities": None, "risks": [], "review_log": None}
    result = apply_review(state, [ReviewAction(action="add", new_risk=_risk(RiskLevel.HIGH))], reviewer="王五")
    assert len(result["risks"]) == 1
    assert result["final_report"].conclusion == "不通过"
