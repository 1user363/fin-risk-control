"""Pydantic 模型单元测试（强结构化校验）。"""

import pytest
from pydantic import ValidationError

from app.models import FinancialEntity, RiskLevel, RiskPoint, RiskType


def test_financial_entity_valid():
    e = FinancialEntity(company_name="X公司", credit_amount=5000.0)
    assert e.company_name == "X公司"
    assert e.credit_amount == 5000.0


def test_financial_entity_rejects_wrong_type():
    """金额传字符串应被 Pydantic 拒绝（强结构化核心）。"""
    with pytest.raises(ValidationError):
        FinancialEntity(company_name="X", credit_amount="五千万元")


def test_riskpoint_rejects_illegal_enum():
    """非法违规类型应被拒绝。"""
    with pytest.raises(ValidationError):
        RiskPoint(
            risk_type="随便写的类型", risk_level=RiskLevel.HIGH,
            description="d", evidence="e", suggestion="s", engine="rule",
        )


def test_riskpoint_serialization():
    """枚举序列化为中文值。"""
    r = RiskPoint(
        risk_type=RiskType.PRINCIPAL_GUARANTEE, risk_level=RiskLevel.HIGH,
        description="d", evidence="e", suggestion="s", engine="rule",
    )
    assert r.model_dump(mode="json")["risk_type"] == "保本承诺"
    assert r.model_dump(mode="json")["risk_level"] == "高"
