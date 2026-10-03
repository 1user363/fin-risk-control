"""FastAPI 应用入口。

职责：创建 FastAPI 实例、挂载 api/ 下所有路由、配置 CORS。
启动：`uvicorn app.main:app --reload`（在 backend 目录下）。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/")
def root():
    return {"service": "金融文本智能风控审查系统", "status": "ok"}
