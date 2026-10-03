"""历史任务与统计接口。

职责：GET /api/tasks —— 历史任务列表；GET /api/stats —— 风险数据统计。
"""

from fastapi import APIRouter

from app.services import db

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/tasks")
def list_tasks():
    return db.list_tasks()


@router.get("/stats")
def get_stats():
    return db.get_stats()
