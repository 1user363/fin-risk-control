# Agent 输入/输出契约

> 定义 5 个 Agent 的职责、输入、输出、依赖。这是各 Agent 独立开发与联调的依据。

## 通用约定

- 所有 Agent 通过 `RiskState`（TypedDict，11 字段）通信，不直接互相调用。
- 节点函数契约：入参 = 完整 `RiskState`，出参 = 只含本节点产出的部分更新 dict，LangGraph 自动合并。
- 状态流转：`pending → parsing → extracting → identifying → reporting → （reviewing → done）`。

---

## Agent ① 文档解析（doc_parser）

- **文件**：`agents/doc_parser.py` + `services/ocr.py`
- **职责**：把 PDF / 图片 / 扫描件解析成纯净文本（去水印/乱码/页码）
- **输入**：`RiskState.file_path`（文档本地路径）
- **输出**：`RiskState.doc_text`（纯净文本）
- **依赖**：PyMuPDF（文本层 PDF）、RapidOCR（扫描件/图片）
- **关键逻辑**：PDF 文本层为空（`len < 10`）时自动切换 OCR

## Agent ② 实体抽取（entity_extractor）

- **文件**：`agents/entity_extractor.py` + `models/entities.py`
- **职责**：抽取金融结构化实体，强制 JSON 输出
- **输入**：`RiskState.doc_text`
- **输出**：`RiskState.entities`（`FinancialEntity`，18 字段）
- **依赖**：`core/llm.py` 的 `structured_llm`（`with_structured_output(FinancialEntity)`）
- **关键点**：字段 description 带「原文X→输出Y」正反例，保证单位统一（万元/百分数）、归一化（币种代码/担保方式）

### FinancialEntity 字段（18）

企业名称、统一社会信用代码、授信金额(万元)、币种、授信期限(月)、年化利率(%)、
负债总额(万元)、资产负债率(%)、应收账款规模、对外担保金额、履约到期日、担保主体列表、
担保方式、是否逾期、逾期详情、涉诉情况、主营业务、法定代表人

## Agent ③ 风险识别（risk_identifier）

- **文件**：`agents/risk_identifier.py` + `services/rule_engine.py` + `services/faiss_store.py`
- **职责**：三引擎判别风险点并定级
- **输入**：`RiskState.doc_text` + `RiskState.entities`
- **输出**：`RiskState.risks`（`list[RiskPoint]`）
- **依赖**：规则引擎、语义引擎（LLM）、FAISS 向量检索

### 三引擎

| 引擎 | 机制 | 特点 |
|---|---|---|
| 规则引擎 | 关键词 + 阈值 + 矛盾检测 | 快、准、可解释（`engine="rule"`） |
| 语义引擎 | LLM 判断隐性风险 | 抓绕过关键词的表述（`engine="semantic"`） |
| 向量检索 | FAISS 检索法规/案例，注入语义 prompt | 辅助判定合规边界 |

### RiskPoint 字段

risk_type（四类：夸大收益/保本承诺/债务异常/虚假披露）、risk_level（高/中/低）、
description、evidence（原文依据）、suggestion、engine（rule/semantic/both）

## Agent ④ 报告生成（report_generator）

- **文件**：`agents/report_generator.py` + `templates/report.md.j2`
- **职责**：汇总实体、风险点，生成标准化审查报告
- **输入**：`RiskState` 全部字段
- **输出**：`RiskState.report`（`Report`）
- **依赖**：Jinja2 模板渲染 Markdown
- **结论判定**：无风险→通过；有高风险→不通过；只有中/低风险→需人工复核

### Report 字段

task_id、file_name、conclusion、entities、risks、risk_summary、suggestions

## Agent ⑤ 人工复核（human_review，交互式）

- **文件**：`agents/human_review.py` + `models/review.py`
- **职责**：应用复核动作，记录日志，生成终审报告
- **输入**：`RiskState.risks` + 复核动作列表（`ReviewAction`）
- **输出**：`RiskState.risks`（更新后）、`review_log`、`final_report`
- **依赖**：`report_generator.build_report`（复用报告构建）
- **注意**：不走自动流水线，由 API 在流水线跑完后触发

### ReviewAction 动作类型

confirm（确认）/ modify（修改字段）/ add（新增）/ revoke（驳回）

复核日志记录：谁、何时、动作、字段、改前值、改后值、备注（对应 `review_log` 表）
