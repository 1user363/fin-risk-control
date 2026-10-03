# 面向券商的多 Agent 金融文本智能风控审查系统

> AI 初审 + 人工复核的券商金融文本合规审查系统，基于 LangGraph 编排 5 个专用 Agent。

## 技术栈
Python · LangGraph · FastAPI · Pydantic v2 · FAISS · MySQL 8 · RapidOCR · Vue3
LLM 走 OpenAI 兼容协议（可切 DeepSeek / Qwen / GLM）。

## 目录说明
- `backend/` — 后端（5 Agent + 编排 + 服务 + API）
- `docs/` — 设计文档（架构、Agent 契约）
- `frontend/` — Vue3 前端（Phase 4 脚手架生成）

## 5 个 Agent 流水线
文档解析 → 实体抽取 → 风险识别(规则+语义双引擎) → 报告生成 → 人工复核
