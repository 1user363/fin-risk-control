"""人工复核动作模型。"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.risks import RiskPoint


class ReviewAction(BaseModel):
    """人工复核动作（前端/API 传入，对应 schema 的 review_log.action）。

    - confirm：确认风险点无误
    - modify：修改风险点的某个字段（如 risk_level）
    - add：新增一个风险点
    - revoke：驳回/删除误判的风险点
    """

    action: Literal["confirm", "modify", "add", "revoke"] = Field(description="动作类型")
    risk_index: Optional[int] = Field(None, description="目标风险点在 risks 列表的下标（confirm/modify/revoke 时）")
    field_name: Optional[str] = Field(None, description="被修改的字段名（modify 时），如 risk_level")
    new_value: Optional[str] = Field(None, description="新值（modify 时，字符串形式，内部转类型）")
    new_risk: Optional[RiskPoint] = Field(None, description="新增的风险点（add 时）")
    remark: Optional[str] = Field(None, description="复核备注")
