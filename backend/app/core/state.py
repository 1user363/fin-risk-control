"""RiskState —— LangGraph 全局共享状态对象（流水线上流动的「工件」）。

职责：
- 5 个 Agent 之间唯一的通信通道；Agent 之间不直接调用，只读写这个状态。
- 每个 Agent 只负责「读取它需要的字段、写入它产出的字段」，互不越界。

生命周期（status 字段的流转）：
    pending → parsing → extracting → identifying → reporting → reviewing → done
                                    （任一步出错 → error，可从出错节点重试）
"""

from typing import Optional, TypedDict

from app.models.entities import FinancialEntity
from app.models.report import Report
from app.models.risks import RiskPoint

# ---- 流程状态常量 ----
STATUS_PENDING = "pending"          # 初始：任务已创建，待处理
STATUS_PARSING = "parsing"          # ① 文档解析中
STATUS_EXTRACTING = "extracting"    # ② 实体抽取中
STATUS_IDENTIFYING = "identifying"  # ③ 风险识别中
STATUS_REPORTING = "reporting"      # ④ 报告生成中
STATUS_REVIEWING = "reviewing"      # ⑤ 等待人工复核
STATUS_DONE = "done"                # 终审完成
STATUS_ERROR = "error"              # 出错中断（error 字段记录原因）


class RiskState(TypedDict):
    """贯穿 5 个 Agent 的共享状态。

    所有字段在初始状态里都已就位（值 None），随流水线逐节点填充。
    """

    # ===== 输入（外部传入，全程只读） =====
    task_id: str                      # 审查任务唯一 ID（对应 MySQL 任务表主键）
    file_path: str                    # 上传文档的本地路径（如 backend/data/xxx.pdf）
    file_name: str                    # 原始文件名（用于报告展示）

    # ===== 各 Agent 产出（依次填充） =====
    doc_text: Optional[str]           # ① 文档解析：清洗后的纯净文本
    entities: Optional[FinancialEntity]   # ② 实体抽取：结构化实体（Pydantic 模型）
    risks: Optional[list[RiskPoint]]      # ③ 风险识别：风险点列表（Pydantic 模型）
    report: Optional[Report]              # ④ 报告生成：标准化审查报告（Pydantic 模型）

    # ===== 人工复核 =====
    review_log: Optional[list[dict]]  # 复核操作轨迹：谁 / 何时 / 改了什么 / 改前→改后
    final_report: Optional[Report]    # ⑤ 终审报告（复核通过后的最终版本）

    # ===== 流程控制 =====
    status: str                       # 当前所处阶段（见顶部 STATUS_* 常量）
    error: Optional[str]              # 出错信息；为 None 表示一切正常


def create_initial_state(
    task_id: str,
    file_path: str,
    file_name: str = "",
) -> RiskState:
    """构造一份「全字段就位」的初始状态，作为 LangGraph 流水线的输入。

    为什么每个字段都显式给 None：让所有节点都能安全地 `state["doc_text"]`
    直接取值（不会 KeyError），读到 None 即表示「上一步还没产出」。
    """
    return RiskState(
        task_id=task_id,
        file_path=file_path,
        file_name=file_name,
        doc_text=None,
        entities=None,
        risks=None,
        report=None,
        review_log=None,
        final_report=None,
        status=STATUS_PENDING,
        error=None,
    )
