"""规则引擎服务（硬规则，快速且可解释）。

职责：用关键词 + 数值阈值快速判定显性风险，覆盖
保本承诺 / 夸大收益 / 债务异常 / 虚假披露 四类高频场景。

为什么需要规则引擎（对应文档「规则 + 语义双引擎」）：
- 快：纯字符串/数值判断，毫秒级，不调 LLM；
- 准：显性违规（如"保本""零风险"）用规则兜底，不依赖模型；
- 可解释：每条命中都能给出「命中的词 / 超出的阈值」，审计友好。

入口：check(doc_text, entities) -> list[RiskPoint]

注：规则当前硬编码在代码里；schema.sql 的 rule 表是为未来「规则可配置化」预留的。
"""

from typing import Optional

from app.models import RiskLevel, RiskPoint, RiskType


# ============ 关键词规则 ============
# 每条规则：命中任一词 → 产生一个风险点
KEYWORD_RULES = [
    {
        "risk_type": RiskType.PRINCIPAL_GUARANTEE,
        "risk_level": RiskLevel.HIGH,
        "keywords": ["保本", "保证本金", "零风险", "稳赚不赔", "本金无忧", "只赚不亏", "本金保障"],
        "description": "出现保本/零风险等违规承诺表述",
        "suggestion": "删除所有保本承诺表述，不得明示或暗示本金无风险",
    },
    {
        "risk_type": RiskType.EXAGGERATED_RETURN,
        "risk_level": RiskLevel.HIGH,
        "keywords": ["稳赚", "高收益", "暴利", "翻倍收益", "躺赚", "超高回报", "保底收益", "收益承诺"],
        "description": "出现夸大收益/收益承诺表述",
        "suggestion": "删除夸大收益表述，收益描述需符合监管要求并充分提示风险",
    },
]

# ============ 阈值规则 ============
# 作用在实体抽取出的字段上（entity 的数值字段）
THRESHOLD_RULES = [
    {
        "risk_type": RiskType.DEBT_ABNORMALITY,
        "risk_level": RiskLevel.HIGH,
        "field": "debt_ratio",
        "operator": ">=",
        "threshold": 100,
        "description": "资产负债率≥100%，资不抵债",
        "suggestion": "重点核查偿债能力，存在重大偿债风险",
    },
    {
        "risk_type": RiskType.DEBT_ABNORMALITY,
        "risk_level": RiskLevel.MEDIUM,
        "field": "debt_ratio",
        "operator": ">=",
        "threshold": 80,
        "description": "资产负债率≥80%，负债水平偏高",
        "suggestion": "关注负债结构及偿债安排，提示偿债压力",
    },
]


def _find_evidence(text: str, keyword: str, context: int = 25) -> str:
    """在原文中定位命中关键词，返回带上下文的片段（供人工复核定位）。"""
    idx = text.find(keyword)
    if idx == -1:
        return keyword
    start = max(0, idx - context)
    end = min(len(text), idx + len(keyword) + context)
    return text[start:end]


def _compare(value, operator: str, threshold) -> bool:
    """比较 value 和 threshold（支持 > >= < <= ==）。"""
    ops = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
    }
    if operator not in ops:
        raise ValueError(f"不支持的比较符: {operator}")
    return ops[operator](value, threshold)


def _check_disclosure_contradiction(text: str) -> Optional[RiskPoint]:
    """检测披露前后矛盾（虚假披露的一种可规则化情形）。

    例：既声明"无逾期"，又出现"逾期贷款/逾期未还"等正面逾期记录。
    """
    no_overdue = any(w in text for w in ["无逾期", "未逾期", "不存在逾期", "无任何逾期"])
    positive_overdue = any(w in text for w in ["逾期贷款", "逾期未还", "存在逾期", "逾期记录为"])
    if no_overdue and positive_overdue:
        return RiskPoint(
            risk_type=RiskType.FALSE_DISCLOSURE,
            risk_level=RiskLevel.HIGH,
            description="披露前后矛盾：既声明无逾期，又出现逾期记录",
            evidence=_find_evidence(text, "逾期"),
            suggestion="核实真实逾期情况，修正披露信息，确保前后一致",
            engine="rule",
        )
    return None


def check(doc_text: str, entities=None) -> list[RiskPoint]:
    """运行规则引擎，返回命中的风险点列表。

    Args:
        doc_text: 解析后的文档纯文本
        entities: 抽取出的 FinancialEntity（可为 None，此时跳过阈值规则）

    Returns:
        命中的风险点列表（可能为空）
    """
    risks: list[RiskPoint] = []
    text = doc_text or ""

    # 1. 关键词规则
    for rule in KEYWORD_RULES:
        for kw in rule["keywords"]:
            if kw in text:
                risks.append(
                    RiskPoint(
                        risk_type=rule["risk_type"],
                        risk_level=rule["risk_level"],
                        description=rule["description"],
                        evidence=_find_evidence(text, kw),
                        suggestion=rule["suggestion"],
                        engine="rule",
                    )
                )
                break  # 同一规则命中一次即可，不重复

    # 2. 阈值规则（需要实体数据）
    # 同一 (字段, 类型) 只报最严重的一条：规则按严重度降序排列，命中即标记，
    # 避免 debt_ratio=120 同时报「≥100」和「≥80」两条冗余风险。
    if entities is not None:
        seen: set = set()
        for rule in THRESHOLD_RULES:
            key = (rule["field"], rule["risk_type"])
            if key in seen:
                continue
            value = getattr(entities, rule["field"], None)
            if value is not None and _compare(value, rule["operator"], rule["threshold"]):
                risks.append(
                    RiskPoint(
                        risk_type=rule["risk_type"],
                        risk_level=rule["risk_level"],
                        description=rule["description"],
                        evidence=f"{rule['field']} = {value}（阈值 {rule['operator']} {rule['threshold']}）",
                        suggestion=rule["suggestion"],
                        engine="rule",
                    )
                )
                seen.add(key)

    # 3. 披露矛盾检测
    contradiction = _check_disclosure_contradiction(text)
    if contradiction is not None:
        risks.append(contradiction)

    return risks
