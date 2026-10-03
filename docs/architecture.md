# 系统架构设计

> 面向券商的多 Agent 金融文本智能风控审查系统 —— 架构与设计文档

## 一、项目概述

针对券商风控业务中，上市公司公告、企业授信资料、营销宣传文稿等海量金融文本
**人工审核效率低、风险漏判率高、标准化程度差**的痛点，基于 LangGraph 构建一套
多 Agent 智能风控审查系统，实现「AI 初审 + 人工复核」的人机协同风控闭环。

## 二、技术栈

| 层次 | 技术 | 说明 |
|---|---|---|
| Agent 编排 | LangGraph 1.x | 状态机式流水线，节点可独立替换 |
| LLM 接入 | LangChain + langchain-openai | OpenAI 兼容协议，可切 DeepSeek / Qwen / GLM |
| 结构化输出 | Pydantic v2 | `with_structured_output` 强制 JSON |
| 向量检索 | FAISS + langchain-community | 金融合规专属知识库 |
| 文档解析 | PyMuPDF + RapidOCR | 文本层 PDF 直接提取，扫描件走 OCR |
| Web 框架 | FastAPI + uvicorn | 高性能接口层 |
| 数据存储 | MySQL 8（兼容 MariaDB 10.4） | 11 张表持久化 |
| 大模型 | DeepSeek（聊天）+ 硅基流动 Qwen3-Embedding（向量） | 混合接入 |

## 三、系统架构（分层）

```
┌─────────────────────────────────────────────────────┐
│                     API 层（FastAPI）                 │
│   upload / review / report / tasks / stats           │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│                    Agents 层（5 Agent）               │
│  ① 文档解析 → ② 实体抽取 → ③ 风险识别 → ④ 报告生成   │
│  （流水线，LangGraph 编排，RiskState 在节点间流转）     │
│                      ⑤ 人工复核（交互式，不走流水线）   │
└────────────┬──────────────────────────┬─────────────┘
             │                          │
┌────────────▼─────────────┐  ┌─────────▼──────────────┐
│      Services 层（工具）   │  │   Models 层（Pydantic） │
│  ocr / faiss_store /     │  │  FinancialEntity /      │
│  rule_engine / db        │  │  RiskPoint / Report /   │
└────────────┬─────────────┘  │  ReviewAction           │
             │                └────────────────────────┘
┌────────────▼─────────────┐
│        DB（MySQL 11 表）   │
└──────────────────────────┘
```

## 四、核心数据流

```
文件上传 → ① 文档解析(纯文本) → ② 实体抽取(结构化JSON) → ③ 风险识别(规则+语义+向量)
        → ④ 报告生成(初审报告) → 【人工复核】→ 终审报告 + 复核日志
```

**状态流转**：`RiskState` 是贯穿全流程的唯一数据通道（11 字段），Agent 之间不直接调用，
只读写 `RiskState`，保证高内聚低耦合。

**风险识别三引擎**（核心难点）：
1. **规则引擎**：关键词/正则/阈值，快速兜底显性违规（可解释）
2. **语义引擎**：LLM 识别绕过关键词的隐性风险
3. **向量检索**：FAISS 检索语义相关的法规/案例，注入 prompt 辅助判定

## 五、目录结构

```
backend/
├── app/
│   ├── agents/          # 5 个 Agent（各一个文件）
│   ├── core/            # state.py(RiskState) / graph.py(编排) / llm.py(LLM)
│   ├── models/          # Pydantic 模型（entities/risks/report/review）
│   ├── services/        # ocr / faiss_store / rule_engine / db
│   ├── api/             # FastAPI 路由（upload/review/report/stats）
│   ├── db/schema.sql    # 11 张表 DDL
│   └── main.py          # FastAPI 入口
├── knowledge_base/      # 向量库语料（监管条例/合规准则/案例）
├── templates/           # Jinja2 报告模板
├── data/                # 上传文档（运行时，gitignore）
└── .env                 # 配置（密钥，gitignore）
```

## 六、关键设计决策

1. **多 Agent 解耦**：Agent 间只通过 `RiskState` 通信，换模型/换 OCR/换报告模板只动单节点。
2. **强结构化输出**：Pydantic `with_structured_output` + `method="function_calling"`
   （DeepSeek 不支持 json_schema 响应格式），失败可重试。
3. **三引擎风险判别**：规则兜底 + 语义补漏 + 向量辅助，降低假阳性、突破关键词局限。
4. **报告存 JSON 快照**：归档件保留当时点状数据，可审计、可溯源。
5. **人工复核独立于流水线**：交互式，记录改前→改后轨迹，生成终审报告。

## 七、API 接口清单

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/upload | 上传文档，落盘 + 建任务 |
| POST | /api/review/{task_id} | 触发 AI 审查流水线 |
| GET | /api/report/{task_id} | 查询初审报告 |
| GET | /api/tasks | 历史任务列表 |
| GET | /api/stats | 风险数据统计 |

## 八、数据库表（11 张）

- **业务流转**：document（文档）、task（任务）、entity（实体）、risk（风险点）、report（报告）、review_log（复核日志）
- **支撑数据**：user（用户）、rule（规则库）、knowledge_item（知识库条目）、risk_case（历史案例）
- **看板统计**：risk_stat（每日统计）
