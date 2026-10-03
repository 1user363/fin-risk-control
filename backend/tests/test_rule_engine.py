"""规则引擎单元测试。"""

from app.models import FinancialEntity, RiskType
from app.services import rule_engine


def test_keyword_rules_hit():
    """含「保本」「稳赚不赔」应命中保本承诺 + 夸大收益。"""
    risks = rule_engine.check("本产品保本保息，稳赚不赔")
    types = {r.risk_type for r in risks}
    assert RiskType.PRINCIPAL_GUARANTEE in types
    assert RiskType.EXAGGERATED_RETURN in types


def test_threshold_rule_and_dedup():
    """资产负债率 120% 应只报一条最严重的债务异常（去重）。"""
    e = FinancialEntity(company_name="X公司", debt_ratio=120.0)
    risks = rule_engine.check("", e)
    debt_risks = [r for r in risks if r.risk_type == RiskType.DEBT_ABNORMALITY]
    assert len(debt_risks) == 1  # 不会同时报 ≥100 和 ≥80


def test_no_false_positive():
    """正常文本 + 正常负债率不应误报。"""
    e = FinancialEntity(company_name="Y公司", debt_ratio=60.0)
    risks = rule_engine.check("公司经营状况良好，无逾期记录", e)
    assert risks == []


def test_contradiction_detection():
    """「无逾期」与「逾期贷款」同时出现应命中虚假披露。"""
    risks = rule_engine.check("本公司无逾期记录，但此前有一笔逾期贷款200万元未结清")
    assert any(r.risk_type == RiskType.FALSE_DISCLOSURE for r in risks)
