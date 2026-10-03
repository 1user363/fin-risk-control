"""报告查询接口。

职责：GET /api/report/{task_id} —— 查询初审报告（含 JSON 快照）。
"""

import json

from fastapi import APIRouter, HTTPException

from app.services import db

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{task_id}")
def get_report(task_id: int):
    """查询指定任务的初审报告。"""
    row = db.get_report(task_id, is_final=False)
    if not row:
        raise HTTPException(404, "报告不存在（可能尚未审查）")
    return {
        "task_id": row["task_id"],
        "conclusion": row["conclusion"],
        "risk_summary": row["risk_summary"],
        "report": json.loads(row["report_json"]) if row["report_json"] else None,
    }
