"""审查报告 Pydantic 模型（报告生成 Agent 的最终数据结构）。

汇总文档解析结果、实体结构化数据、风险点、合规建议。
通过「引用」而不是「复制」实体与风险模型，保证数据不冗余、类型强关联。
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.entities import FinancialEntity
from app.models.risks import RiskPoint


class Report(BaseModel):
    """标准化风控审查报告。"""

    task_id: str = Field(description="审查任务 ID")
    file_name: str = Field(description="被审查文档文件名")
    conclusion: Literal["通过", "需人工复核", "不通过"] = Field(description="初审结论")
    entities: Optional[FinancialEntity] = Field(None, description="抽取出的结构化实体")
    risks: list[RiskPoint] = Field(default_factory=list, description="识别出的风险点列表")
    risk_summary: str = Field(description="风险汇总结论（一段话）")
    suggestions: list[str] = Field(default_factory=list, description="综合合规建议列表")
