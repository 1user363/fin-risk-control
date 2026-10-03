"""报告查询与导出接口。

职责：GET /api/report/{task_id} —— 查询初审报告（JSON）；
      GET /api/report/{task_id}/export —— 导出 PDF。
"""

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.agents.report_generator import render_report_pdf
from app.models import Report
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


@router.get("/report/{task_id}/export")
def export_report(task_id: int):
    """导出指定任务的初审报告为 PDF。"""
    row = db.get_report(task_id, is_final=False)
    if not row or not row["report_json"]:
        raise HTTPException(404, "报告不存在（可能尚未审查）")

    report = Report.model_validate_json(row["report_json"])
    pdf_bytes = render_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{task_id}.pdf"'},
    )
