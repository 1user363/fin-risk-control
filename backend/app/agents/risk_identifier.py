"""智能风险识别 Agent（流水线第 3 步）。

职责：规则引擎 + 语义引擎双判别，识别风险点并定级。
输入：RiskState.doc_text + RiskState.entities
输出：风险点列表 -> 写入 RiskState.risks
依赖：services/rule_engine.py（硬规则）、core/llm.py（语义引擎）
"""

from app.core.llm import structured_llm
from app.core.state import STATUS_IDENTIFYING, RiskState
from app.models import RiskDetection, RiskPoint
from app.services import faiss_store, rule_engine

# 语义引擎提示词：重点抓「绕过关键词」的隐性风险；注入 FAISS 检索到的法规案例辅助判定
SEMANTIC_PROMPT = """你是金融风控合规专家。请判断下面文档是否存在合规风险，重点识别四类：
1. 夸大收益、2. 保本承诺、3. 债务异常、4. 虚假披露。

以下是从知识库检索到的相关法规/案例（供参考，帮助判定合规边界）：
---
{context}
---

要特别注意「隐性、绕过关键词」的表述，例如：
- "收益有保障""稳了""放心投" = 变相保本/夸大收益
- "几乎无风险""随便赚" = 变相保本承诺

要求：
- 只报告文档中真实存在的风险，不要无中生有；
- 每个风险点给全：risk_type、risk_level(高/中/低)、description、evidence(原文片段)、suggestion(整改建议)；
- engine 字段一律填 "semantic"。

文档内容：
---
{doc_text}
---
"""


def _semantic_detect(doc_text: str) -> list[RiskPoint]:
    """语义引擎：FAISS 检索相关法规案例 + LLM 识别隐性/模糊风险。"""
    # 向量检索：找出语义最相关的法规/案例（突破关键词局限）
    contexts = faiss_store.search(doc_text, k=3)
    context_str = "\n".join(f"- {c}" for c in contexts)

    prompt = SEMANTIC_PROMPT.format(doc_text=doc_text, context=context_str)
    runner = structured_llm(RiskDetection)
    result = runner.invoke(prompt)
    risks = result.risks
    # engine 是技术元数据，不信任 LLM 填对，强制标记为 semantic
    for r in risks:
        r.engine = "semantic"
    return risks


def identify_risks(state: RiskState) -> dict:
    """节点③：规则引擎 + 语义引擎双判定，合并产出风险点列表。"""
    doc_text = state.get("doc_text") or ""
    entities = state.get("entities")

    # 硬规则：快、准、可解释，兜底显性违规
    rule_risks = rule_engine.check(doc_text, entities)
    # 语义引擎：抓规则漏掉的隐性风险（文档为空则跳过）
    semantic_risks = _semantic_detect(doc_text) if doc_text.strip() else []

    risks = rule_risks + semantic_risks
    return {"risks": risks, "status": STATUS_IDENTIFYING}
