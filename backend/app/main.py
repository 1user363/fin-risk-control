"""FastAPI 应用入口。

职责：创建 FastAPI 实例、挂载 api/ 路由、配置 CORS；
生产部署时（前端已 build）托管 frontend/dist 静态文件，实现单服务部署。

启动：`uvicorn app.main:app --reload`（开发）；`uvicorn app.main:app`（生产）。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import report, review, stats, upload

app = FastAPI(title="金融文本智能风控审查系统", version="0.1.0")

# CORS：开发环境放开，生产环境要收紧到具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(review.router)
app.include_router(report.router)
app.include_router(stats.router)

# 生产部署：前端 build 后（frontend/dist 存在）由后端托管静态文件，实现单服务部署
DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")
else:

    @app.get("/")
    def root():
        return {"service": "金融文本智能风控审查系统", "status": "ok"}
