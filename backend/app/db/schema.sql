-- ============================================================
-- 数据库表结构（MySQL 8，库名 risk_control）
-- 面向券商的多 Agent 金融文本智能风控审查系统
--
-- 11 张表，分三类：
--   [业务流转] document / task / entity / risk / report / review_log
--   [支撑数据] user / rule / knowledge_item / risk_case
--   [看板统计] risk_stat
--
-- 关键设计决策：
--   1. 金额一律 DECIMAL 不用 FLOAT —— 钱不能有浮点误差；
--      注意 Pydantic 模型里是 float（大模型输出浮点数），存库时由服务层转 Decimal。
--   2. 列表字段（如担保主体 guarantors）用 JSON 列 —— MySQL 8 原生支持。
--   3. 报告存「JSON 快照」而非外键引用 —— 报告是归档件，即使后续实体/风险被复核修改，
--      归档报告仍保留当时的点状数据（可审计）。
--   4. 状态/等级/类型用 ENUM —— 约束取值范围，非法值直接拒绝。
-- ============================================================

CREATE DATABASE IF NOT EXISTS risk_control
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE risk_control;

-- ============================================================
-- ① user：系统用户（风控人员）
-- ============================================================
CREATE TABLE `user` (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  username      VARCHAR(64)     NOT NULL COMMENT '登录名',
  password_hash VARCHAR(255)    NOT NULL COMMENT '密码哈希（绝不存明文）',
  real_name     VARCHAR(64)     DEFAULT NULL COMMENT '真实姓名',
  role          ENUM('admin','reviewer') NOT NULL DEFAULT 'reviewer' COMMENT '角色：admin=管理员 / reviewer=风控复核员',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

-- ============================================================
-- ② document：上传文档（文件元信息 + 解析缓存）
-- ============================================================
CREATE TABLE `document` (
  id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  file_name VARCHAR(255)    NOT NULL COMMENT '原始文件名',
  file_path VARCHAR(512)    NOT NULL COMMENT '本地存储路径',
  file_type VARCHAR(16)     NOT NULL COMMENT '文件类型：pdf/jpg/png/docx',
  file_size INT UNSIGNED    DEFAULT NULL COMMENT '文件大小（字节）',
  file_hash VARCHAR(64)     DEFAULT NULL COMMENT 'SHA256 哈希，用于去重',
  doc_text  LONGTEXT        DEFAULT NULL COMMENT '解析后的纯净文本（缓存，避免重复 OCR）',
  created_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_hash (file_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='上传文档表';

-- ============================================================
-- ③ task：审查任务（一次审查 = 一个任务，贯穿 5 Agent 的状态机）
-- ============================================================
CREATE TABLE `task` (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_no     VARCHAR(32)     NOT NULL COMMENT '任务编号（如 T20261003-0001，对外展示）',
  document_id BIGINT UNSIGNED NOT NULL COMMENT '关联文档',
  status      VARCHAR(16)     NOT NULL DEFAULT 'pending' COMMENT '状态：pending/parsing/extracting/identifying/reporting/reviewing/done/error',
  conclusion  VARCHAR(16)     DEFAULT NULL COMMENT '初审结论：通过/需人工复核/不通过',
  error_msg   VARCHAR(512)    DEFAULT NULL COMMENT '出错信息（status=error 时）',
  reviewer_id BIGINT UNSIGNED DEFAULT NULL COMMENT '复核人（关联 user，进入人工复核后填写）',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_task_no (task_no),
  KEY idx_status (status),
  KEY idx_created (created_at),
  CONSTRAINT fk_task_document FOREIGN KEY (document_id) REFERENCES document (id),
  CONSTRAINT fk_task_reviewer FOREIGN KEY (reviewer_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查任务表';

-- ============================================================
-- ④ entity：实体抽取结果（一一对应 models.FinancialEntity 的 18 个字段）
-- 1 任务 : 1 实体
-- ============================================================
CREATE TABLE `entity` (
  id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id               BIGINT UNSIGNED NOT NULL COMMENT '关联任务',
  company_name          VARCHAR(255)    NOT NULL COMMENT '企业全称',
  credit_code           VARCHAR(32)     DEFAULT NULL COMMENT '统一社会信用代码',
  credit_amount         DECIMAL(18,2)   DEFAULT NULL COMMENT '授信金额（万元）',
  currency              VARCHAR(8)      NOT NULL DEFAULT 'CNY' COMMENT '币种',
  credit_term_months    INT             DEFAULT NULL COMMENT '授信期限（月）',
  interest_rate         DECIMAL(6,2)    DEFAULT NULL COMMENT '年化利率（%）',
  total_liability       DECIMAL(18,2)   DEFAULT NULL COMMENT '负债总额（万元）',
  debt_ratio            DECIMAL(6,2)    DEFAULT NULL COMMENT '资产负债率（%）',
  accounts_receivable   DECIMAL(18,2)   DEFAULT NULL COMMENT '应收账款规模（万元）',
  external_guarantee    DECIMAL(18,2)   DEFAULT NULL COMMENT '对外担保金额（万元）',
  due_date              DATE            DEFAULT NULL COMMENT '履约到期日',
  guarantors            JSON            DEFAULT NULL COMMENT '担保主体列表（JSON 数组）',
  guarantee_type        VARCHAR(16)     DEFAULT NULL COMMENT '担保方式：抵押/质押/保证/信用',
  has_overdue           TINYINT(1)      DEFAULT NULL COMMENT '是否逾期：0=否 1=是 NULL=未提及',
  overdue_detail        TEXT            DEFAULT NULL COMMENT '逾期情况描述',
  litigation            TEXT            DEFAULT NULL COMMENT '涉诉情况描述',
  main_business         TEXT            DEFAULT NULL COMMENT '主营业务',
  legal_representative  VARCHAR(64)     DEFAULT NULL COMMENT '法定代表人',
  created_at            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_task (task_id),
  CONSTRAINT fk_entity_task FOREIGN KEY (task_id) REFERENCES task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实体抽取结果表';

-- ============================================================
-- ⑤ risk：风险点（一一对应 models.RiskPoint）
-- 1 任务 : N 风险点；额外加 review_status 支持人工复核流转
-- ============================================================
CREATE TABLE `risk` (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id       BIGINT UNSIGNED NOT NULL COMMENT '关联任务',
  risk_type     VARCHAR(16)     NOT NULL COMMENT '违规类型：夸大收益/保本承诺/债务异常/虚假披露',
  risk_level    ENUM('高','中','低') NOT NULL COMMENT '风险等级',
  description   TEXT            NOT NULL COMMENT '风险描述',
  evidence      TEXT            NOT NULL COMMENT '命中的原文片段',
  suggestion    TEXT            NOT NULL COMMENT '合规整改建议',
  engine        ENUM('rule','semantic','both') NOT NULL COMMENT '判定引擎',
  review_status ENUM('pending','confirmed','modified','revoked') NOT NULL DEFAULT 'pending' COMMENT '复核状态：待复核/确认/已修改/已驳回',
  reviewed_by   BIGINT UNSIGNED DEFAULT NULL COMMENT '复核人（关联 user）',
  created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (id),
  KEY idx_task (task_id),
  KEY idx_type (risk_type),
  CONSTRAINT fk_risk_task FOREIGN KEY (task_id) REFERENCES task (id),
  CONSTRAINT fk_risk_reviewer FOREIGN KEY (reviewed_by) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风险点表';

-- ============================================================
-- ⑥ report：审查报告（存 JSON 快照 + 渲染正文，可归档）
-- 1 任务 : 至多 2 份（初审 + 终审），is_final 区分
-- ============================================================
CREATE TABLE `report` (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id         BIGINT UNSIGNED NOT NULL COMMENT '关联任务',
  is_final        TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '0=初审报告 1=终审报告',
  conclusion      VARCHAR(16)     DEFAULT NULL COMMENT '结论：通过/需人工复核/不通过',
  risk_summary    TEXT            DEFAULT NULL COMMENT '风险汇总结论',
  report_json     JSON            DEFAULT NULL COMMENT '完整报告 JSON 快照（含实体/风险/建议，用于归档）',
  report_markdown LONGTEXT        DEFAULT NULL COMMENT '渲染后的报告正文（Markdown）',
  created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_task (task_id),
  CONSTRAINT fk_report_task FOREIGN KEY (task_id) REFERENCES task (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查报告表';

-- ============================================================
-- ⑦ review_log：人工复核记录（审计轨迹：谁/何时/改了什么/改前→改后）
-- ============================================================
CREATE TABLE `review_log` (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  task_id     BIGINT UNSIGNED NOT NULL COMMENT '关联任务',
  risk_id     BIGINT UNSIGNED DEFAULT NULL COMMENT '针对的风险点（NULL=针对实体或整体）',
  reviewer_id BIGINT UNSIGNED NOT NULL COMMENT '操作人（关联 user）',
  action      ENUM('confirm','modify','add','revoke') NOT NULL COMMENT '动作：确认/修改/新增/驳回',
  field_name  VARCHAR(64)     DEFAULT NULL COMMENT '被修改的字段（如 risk_level）',
  old_value   VARCHAR(512)    DEFAULT NULL COMMENT '修改前值',
  new_value   VARCHAR(512)    DEFAULT NULL COMMENT '修改后值',
  remark      VARCHAR(512)    DEFAULT NULL COMMENT '复核备注',
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  PRIMARY KEY (id),
  KEY idx_task (task_id),
  CONSTRAINT fk_rl_task FOREIGN KEY (task_id) REFERENCES task (id),
  CONSTRAINT fk_rl_risk FOREIGN KEY (risk_id) REFERENCES risk (id),
  CONSTRAINT fk_rl_reviewer FOREIGN KEY (reviewer_id) REFERENCES user (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人工复核记录表（审计轨迹）';

-- ============================================================
-- ⑧ rule：风控规则库（规则引擎的硬规则）
-- ============================================================
CREATE TABLE `rule` (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  rule_name  VARCHAR(128)    NOT NULL COMMENT '规则名',
  risk_type  VARCHAR(16)     NOT NULL COMMENT '对应违规类型（四类之一）',
  rule_type  ENUM('keyword','regex','threshold') NOT NULL COMMENT '规则类型：关键词/正则/数值阈值',
  pattern    VARCHAR(512)    DEFAULT NULL COMMENT '关键词或正则表达式（keyword/regex 时用）',
  field_name VARCHAR(64)     DEFAULT NULL COMMENT '阈值作用的字段（如 debt_ratio，threshold 时用）',
  operator   VARCHAR(8)      DEFAULT NULL COMMENT '比较符：>/</>=/<=/==（threshold 时用）',
  threshold  DECIMAL(18,4)   DEFAULT NULL COMMENT '阈值（threshold 时用）',
  risk_level ENUM('高','中','低') NOT NULL DEFAULT '中' COMMENT '命中后判定的风险等级',
  enabled    TINYINT(1)      NOT NULL DEFAULT 1 COMMENT '是否启用：1=启用 0=停用',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_enabled (enabled),
  KEY idx_risk_type (risk_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风控规则库';

-- ============================================================
-- ⑨ knowledge_item：知识库条目（监管条例 / 合规准则，会 embedding 进 FAISS）
-- ============================================================
CREATE TABLE `knowledge_item` (
  id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  category  ENUM('regulation','guideline') NOT NULL COMMENT '类别：regulation=监管条例 / guideline=合规准则',
  title     VARCHAR(255)    NOT NULL COMMENT '标题',
  content   LONGTEXT        NOT NULL COMMENT '原文内容（会 embedding 进 FAISS 向量库）',
  source    VARCHAR(255)    DEFAULT NULL COMMENT '出处（法规文号/链接）',
  vector_id VARCHAR(64)     DEFAULT NULL COMMENT 'FAISS 索引中的向量 ID（关联向量库）',
  created_at DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库条目表';

-- ============================================================
-- ⑩ risk_case：历史风控案例（用于语义检索，辅助判定合规边界）
-- ============================================================
CREATE TABLE `risk_case` (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  case_title VARCHAR(255)    NOT NULL COMMENT '案例标题',
  case_text  LONGTEXT        NOT NULL COMMENT '案例原文（含违规表述）',
  risk_type  VARCHAR(16)     DEFAULT NULL COMMENT '对应违规类型',
  risk_level ENUM('高','中','低') DEFAULT NULL COMMENT '风险等级',
  verdict    TEXT            DEFAULT NULL COMMENT '监管处罚/认定结果',
  vector_id  VARCHAR(64)     DEFAULT NULL COMMENT 'FAISS 向量 ID',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_risk_type (risk_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='历史风控案例表';

-- ============================================================
-- ⑪ risk_stat：风险数据统计（每日汇总，供前端看板，可离线批量更新）
-- ============================================================
CREATE TABLE `risk_stat` (
  id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
  stat_date       DATE            NOT NULL COMMENT '统计日期',
  total_tasks     INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '当日任务总数',
  risk_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '风险点总数',
  high_risk_count INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '高风险点数量',
  pass_count      INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '通过数量',
  review_count    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '需人工复核数量',
  reject_count    INT UNSIGNED    NOT NULL DEFAULT 0 COMMENT '不通过数量',
  PRIMARY KEY (id),
  UNIQUE KEY uk_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='风险数据统计表';
