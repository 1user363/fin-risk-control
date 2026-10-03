"""审查接口。

职责：POST /api/review/{task_id} —— 触发 4 Agent 流水线审查，结果落库。
"""

from fastapi import APIRouter, HTTPException

from app.agents.human_review import apply_review
from app.core.graph import run_pipeline
from app.models import ReviewAction
from app.services import db

router = APIRouter(prefix="/api", tags=["review"])


@router.post("/review/{task_id}")
def trigger_review(task_id: int):
    """触发 AI 审查流水线（文档解析 → 实体抽取 → 风险识别 → 报告生成），结果落库。"""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    document = db.get_document(task["document_id"])
    if not document:
        raise HTTPException(404, "文档不存在")

    # 跑流水线（同步阻塞；含 LLM 调用，耗时数秒，生产环境应改后台任务）
    state = run_pipeline(task["task_no"], document["file_path"], document["file_name"])

    # 出错则记录并返回
    if state.get("error"):
        db.update_task(task_id, status="error", error_msg=state["error"])
        raise HTTPException(500, f"审查失败：{state['error']}")

    # 结果落库
    if state.get("entities"):
        db.save_entity(task_id, state["entities"])
    if state.get("risks"):
        db.save_risks(task_id, state["risks"])
    if state.get("report"):
        db.save_report(task_id, state["report"], is_final=False)
        db.update_task(task_id, status="done", conclusion=state["report"].conclusion)

    report = state.get("report")
    return {
        "task_id": task_id,
        "conclusion": report.conclusion if report else None,
        "risk_summary": report.risk_summary if report else None,
        "risks": [r.model_dump(mode="json") for r in (state.get("risks") or [])],
    }


@router.post("/review/{task_id}/submit")
def submit_review(task_id: int, payload: dict):
    """提交人工复核动作，记录日志并生成终审报告。"""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    document = db.get_document(task["document_id"])

    # 从 DB 重建状态（风险 + 实体）
    state = {
        "task_id": task["task_no"],
        "file_name": document["file_name"],
        "entities": db.get_entity(task_id),
        "risks": db.get_risks(task_id),
        "review_log": None,
    }

    # 应用复核动作
    actions = [ReviewAction(**a) for a in payload.get("actions", [])]
    reviewer = payload.get("reviewer", "未知")
    result = apply_review(state, actions, reviewer=reviewer)

    # 落库：复核日志 + 终审报告
    reviewer_id = db.get_or_create_user(reviewer)
    for entry in result["review_log"]:
        db.save_review_log(task_id, reviewer_id, entry)
    if result["final_report"]:
        db.save_report(task_id, result["final_report"], is_final=True)
        db.update_task(task_id, conclusion=result["final_report"].conclusion)

    return {
        "task_id": task_id,
        "final_conclusion": result["final_report"].conclusion,
        "review_log_count": len(result["review_log"]),
    }
