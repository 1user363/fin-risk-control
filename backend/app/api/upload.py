"""文档上传接口。

职责：POST /api/upload —— 接收文档文件，落盘到 backend/data/，创建 document + task 记录。
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services import db

router = APIRouter(prefix="/api", tags=["upload"])

DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # backend/data
ALLOWED_EXTS = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档，落盘 + 建任务，返回 task_id / task_no。"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    save_name = f"{uuid.uuid4().hex}{ext}"
    save_path = DATA_DIR / save_name
    save_path.write_bytes(await file.read())

    document_id = db.create_document(file.filename, str(save_path), ext.lstrip("."))
    task_no = f"T{uuid.uuid4().hex[:12]}"
    task_id = db.create_task(task_no, document_id)

    return {"task_id": task_id, "task_no": task_no, "file_name": file.filename}
