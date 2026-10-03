"""金融实体抽取 Agent（流水线第 2 步）。

职责：从文档文本中抽取金融结构化实体（企业名称/授信金额/负债/担保/逾期等十余类）。
输入：RiskState.doc_text
输出：经 Pydantic 强校验的 FinancialEntity -> 写入 RiskState.entities
依赖：core/llm.py（structured_llm + with_structured_output）、models/entities.py
"""

from app.core.llm import structured_llm
from app.core.state import STATUS_EXTRACTING, RiskState
from app.models import FinancialEntity

# 抽取提示词：字段的具体说明已写在 FinancialEntity 各字段的 description 里，
# 这里只交代任务 + 两条关键约束（不编造、留空）。
EXTRACTION_PROMPT = """你是金融风控系统的信息抽取专家，请从下面的文档内容中抽取金融实体信息。

要求：
- 只抽取文档中明确出现的信息，绝不推测、编造；
- 未提及的字段请留空（None 或空列表）。

文档内容：
---
{doc_text}
---
"""


def extract_entities(state: RiskState) -> dict:
    """节点②：调用 LLM 强结构化抽取金融实体。

    关键点：structured_llm(FinancialEntity) 把 Pydantic 模型转成 JSON Schema，
    强制 LLM 返回合法 JSON，再由 Pydantic 校验，非法输出直接报错。
    """
    doc_text = state.get("doc_text") or ""
    runner = structured_llm(FinancialEntity)
    entities = runner.invoke(EXTRACTION_PROMPT.format(doc_text=doc_text))
    return {"entities": entities, "status": STATUS_EXTRACTING}
