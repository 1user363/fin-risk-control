# 面向券商的多 Agent 金融文本智能风控审查系统

> AI 初审 + 人工复核的券商金融文本合规审查系统，基于 LangGraph 编排 5 个专用 Agent，实现「文档解析 → 实体抽取 → 三引擎风险识别 → 报告生成 → 人工复核」的全链路自动化。

## ✨ 核心亮点

- **多 Agent 解耦架构**：LangGraph 状态机编排，Agent 间只通过 `RiskState` 通信，可独立替换、迭代
- **三引擎风险判别**：规则引擎（快速可解释）+ 语义引擎（抓隐性风险）+ FAISS 向量检索（突破关键词局限）
- **强结构化输出**：Pydantic v2 + `with_structured_output`，LLM 输出强制 JSON，杜绝随机性
- **人机协同闭环**：复核动作记录改前→改后轨迹，自动生成终审报告，可审计溯源
- **完整工程化**：FastAPI + MySQL 持久化 + 单元测试 + PDF 报告导出 + Vue3 前端

## 🛠 技术栈

| 层次 | 技术 |
|---|---|
| Agent 编排 | LangGraph 1.x |
| LLM 接入 | LangChain + langchain-openai（OpenAI 兼容，可切 DeepSeek/Qwen/GLM） |
| 结构化输出 | Pydantic v2 |
| 向量检索 | FAISS + langchain-community |
| 文档解析 | PyMuPDF + RapidOCR |
| 后端框架 | FastAPI + uvicorn |
| 数据库 | MySQL 8（兼容 MariaDB 10.4） |
| 前端 | Vue3 + Vite + Element Plus + ECharts |
| 测试 | pytest |

## 🏗 系统架构

```
文件上传 → ① 文档解析(纯文本) → ② 实体抽取(结构化JSON) → ③ 风险识别(规则+语义+向量)
        → ④ 报告生成(初审报告) → 【人工复核】→ 终审报告 + 复核日志

风险识别三引擎：
  规则引擎  关键词/阈值快速兜底显性违规（engine="rule"）
  语义引擎  LLM 识别绕过关键词的隐性风险（engine="semantic"）
  向量检索  FAISS 检索法规/案例注入 prompt 辅助判定
```

## 📁 目录结构

```
backend/
├── app/
│   ├── agents/          # 5 个 Agent（文档解析/实体抽取/风险识别/报告生成/人工复核）
│   ├── core/            # state(RiskState) / graph(编排) / llm(LLM)
│   ├── models/          # Pydantic 模型（entities/risks/report/review）
│   ├── services/        # ocr / faiss_store / rule_engine / db
│   ├── api/             # FastAPI 路由
│   ├── db/schema.sql    # 11 张表 DDL
│   └── main.py          # FastAPI 入口
├── knowledge_base/      # 向量库语料（监管条例/案例）
├── templates/           # Jinja2 报告模板
├── tests/               # pytest 单元测试
└── requirements.txt
frontend/                # Vue3 前端（4 页面）
docs/                    # 架构文档 + Agent 契约
```

## 🚀 快速开始

### 前置要求

- Python 3.14（`py -3.14`，注意本机 `python` 可能指向旧版）
- Node.js ≥ 18
- MySQL 8 / MariaDB

### 1. 后端

```bash
# 建虚拟环境 + 装依赖
cd backend
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# 配置环境变量（复制模板，填 LLM key 和 MySQL 密码）
copy .env.example .env

# 初始化数据库（11 张表）
mysql -u root -p --default-character-set=utf8mb4 < app/db/schema.sql

# 启动
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8000
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
# 打开 http://localhost:5173
```

### 3. 运行测试

```bash
cd backend
.venv\Scripts\python.exe -m pytest -v
```

## 📡 API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload` | 上传文档，落盘 + 建任务 |
| POST | `/api/review/{task_id}` | 触发 AI 审查流水线 |
| POST | `/api/review/{task_id}/submit` | 提交人工复核（落日志+终审报告） |
| GET | `/api/report/{task_id}` | 查询初审报告 |
| GET | `/api/report/{task_id}/export` | 导出 PDF 报告 |
| GET | `/api/tasks` | 历史任务列表 |
| GET | `/api/stats` | 风险统计（含类型/等级分布） |

交互式文档：启动后端后访问 `http://127.0.0.1:8000/docs`（Swagger）。

## ⚙️ 环境变量（.env）

```
LLM_BASE_URL=https://api.deepseek.com       # LLM API 地址
LLM_API_KEY=sk-xxx                          # LLM key
LLM_MODEL=deepseek-chat                     # 聊天模型
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1   # 向量模型地址（DeepSeek 无 embedding）
EMBEDDING_API_KEY=sk-xxx                    # 向量模型 key
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B    # 向量模型
MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DB
```

## 📦 生产部署

前端 build 后，后端可托管静态文件实现单服务部署（无需单独跑前端）：

```bash
# 1. 构建前端
cd frontend
npm run build          # 产出 frontend/dist/

# 2. 启动后端（会自动检测到 dist/ 并托管）
cd ../backend
.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir . --host 0.0.0.0 --port 8000

# 3. 访问 http://localhost:8000 即可使用完整系统
```

> 开发模式仍是前后端分离：后端 8000 + 前端 `npm run dev`（5173，代理 /api 到后端）。

## 📄 文档

- `docs/architecture.md` — 系统架构设计
- `docs/agent-specs.md` — 5 个 Agent 的输入/输出契约
- `docs/deploy.md` — 云服务器部署指南
