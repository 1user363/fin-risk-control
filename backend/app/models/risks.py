"""风险点 Pydantic 模型（风险识别 Agent 的输出结构）。

违规类型四类：夸大收益 / 保本承诺 / 债务异常 / 虚假披露。
每个风险点必须能被人工复核「定位到原文」，所以带 evidence 原文片段。
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class RiskType(str, Enum):
    """违规类型（券商风控四类高频场景）。"""

    EXAGGERATED_RETURN = "夸大收益"   # 夸大收益
    PRINCIPAL_GUARANTEE = "保本承诺"  # 保本承诺
    DEBT_ABNORMALITY = "债务异常"     # 债务异常
    FALSE_DISCLOSURE = "虚假披露"     # 虚假披露


class RiskLevel(str, Enum):
    """风险等级。"""

    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


class RiskPoint(BaseModel):
    """单个风险点。"""

    risk_type: RiskType = Field(description="违规类型，四选一")
    risk_level: RiskLevel = Field(description="风险等级：高/中/低")
    description: str = Field(description="风险描述，一句话说清问题所在")
    evidence: str = Field(description="命中的原文片段（人工复核据此定位）")
    suggestion: str = Field(description="合规整改建议")
    engine: Literal["rule", "semantic", "both"] = Field(
        description="判定引擎：rule=规则引擎 / semantic=语义引擎 / both=双引擎命中"
    )


class RiskDetection(BaseModel):
    """语义引擎的风险检测输出（with_structured_output 的顶层 schema）。

    为什么需要这个包装类：with_structured_output 的顶层必须是 BaseModel，
    不能直接传 list[RiskPoint]，所以用一层「含 risks 列表」的模型包住。
    """

    risks: list[RiskPoint] = Field(
        default_factory=list,
        description="识别出的风险点列表；无风险则返回空列表",
    )
