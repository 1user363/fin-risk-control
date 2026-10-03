"""金融实体 Pydantic 模型（实体抽取 Agent 的强结构化输出约束）。

这是给大模型的「答题卡」：定义十余类金融核心字段，实体抽取 Agent 用
with_structured_output(FinancialEntity) 强制大模型按此结构返回 JSON。

设计要点：
- 类型要「可计算」：金额/利率用 float、期限用 int、日期用 date、是否逾期用 bool；
- 单位统一：金额一律万元、利率一律百分数数值、期限一律月；
- 可选字段用 Optional，description 明确「文本未提及则填 None」，避免大模型幻觉编造；
- 每个字段的 description 会转成 JSON Schema 说明，是提升抽取准确率的关键。
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class FinancialEntity(BaseModel):
    """一份金融文档对应的核心结构化实体（单个审查主体）。"""

    # ===== 主体信息 =====
    company_name: str = Field(description="企业全称（必填，任何文档都有主体名称）")
    credit_code: Optional[str] = Field(
        None, description="统一社会信用代码（18 位），文本未提及则填 None"
    )

    # ===== 授信信息 =====
    credit_amount: Optional[float] = Field(
        None, description="授信金额，单位：万元。直接输出数字本身，不要换算单位：原文'5000万元'输出 5000，不要输出 50000000。未提及则 None"
    )
    currency: str = Field("CNY", description="授信币种，只输出标准币种代码（CNY/USD/HKD），不要输出中文（'人民币'应输出 CNY）。默认 CNY")
    credit_term_months: Optional[int] = Field(
        None, description="授信期限，单位：月，只输出纯数字（如 36 表示 36 个月），未提及则 None"
    )
    interest_rate: Optional[float] = Field(
        None, description="年化利率，输出百分号前的数字：原文'4.35%'输出 4.35，不要输出 0.0435。未提及则 None"
    )

    # ===== 财务 / 负债 =====
    total_liability: Optional[float] = Field(
        None, description="负债总额，单位：万元，只输出纯数字，未提及则 None"
    )
    debt_ratio: Optional[float] = Field(
        None, description="资产负债率，输出百分号前的数字：原文'65%'输出 65，不要输出 0.65。未提及则 None"
    )
    accounts_receivable: Optional[float] = Field(
        None, description="应收账款规模，单位：万元，只输出纯数字，未提及则 None"
    )
    external_guarantee: Optional[float] = Field(
        None, description="对外担保金额，单位：万元，只输出纯数字，未提及则 None"
    )

    # ===== 履约 / 担保 =====
    due_date: Optional[date] = Field(
        None, description="履约到期日，格式 YYYY-MM-DD，未提及则 None"
    )
    guarantors: list[str] = Field(
        default_factory=list, description="担保主体列表，可能多个；无担保则为空列表 []"
    )
    guarantee_type: Optional[str] = Field(
        None, description="担保方式，归一化为四选一：抵押/质押/保证/信用。原文'连带责任保证担保'应输出'保证'。未提及则 None"
    )

    # ===== 风险相关 =====
    has_overdue: Optional[bool] = Field(
        None, description="是否存在逾期记录，是填 true、否填 false，未提及则 None"
    )
    overdue_detail: Optional[str] = Field(
        None, description="逾期情况描述（金额/次数/时长），无逾期或未提及则 None"
    )
    litigation: Optional[str] = Field(
        None, description="涉诉情况描述（案件数量/金额/类型），无涉诉或未提及则 None"
    )

    # ===== 其他 =====
    main_business: Optional[str] = Field(None, description="主营业务简述，未提及则 None")
    legal_representative: Optional[str] = Field(None, description="法定代表人姓名，未提及则 None")
