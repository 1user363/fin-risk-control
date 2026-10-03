"""MySQL 连接与数据访问服务。

职责：连接管理（当前每次新建连接，生产环境换连接池）+ 核心表 CRUD。
依赖：db/schema.sql 定义表结构。

序列化约定：Pydantic 模型一律用 model_dump(mode="json") 转成 JSON 友好值
（枚举→中文值、date→"YYYY-MM-DD"），再交给 pymysql。
"""

import json

import pymysql
from pymysql.cursors import DictCursor

from app.config import settings
from app.models import FinancialEntity, RiskLevel, RiskPoint, RiskType


def get_connection():
    """建立 MySQL 连接（autocommit，读取返回字典游标）。"""
    return pymysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DB,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


# ============ 任务 / 文档 ============

def create_document(file_name: str, file_path: str, file_type: str) -> int:
    """创建文档记录，返回 document_id。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO document (file_name, file_path, file_type) VALUES (%s, %s, %s)",
                (file_name, file_path, file_type),
            )
            return cur.lastrowid
    finally:
        conn.close()


def create_task(task_no: str, document_id: int) -> int:
    """创建任务（初始 pending），返回 task_id。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO task (task_no, document_id, status) VALUES (%s, %s, 'pending')",
                (task_no, document_id),
            )
            return cur.lastrowid
    finally:
        conn.close()


def update_task(task_id: int, status: str = None, conclusion: str = None, error_msg: str = None) -> None:
    """按需更新任务状态/结论/错误信息（只更新非 None 字段）。"""
    sets, params = [], []
    if status is not None:
        sets.append("status = %s")
        params.append(status)
    if conclusion is not None:
        sets.append("conclusion = %s")
        params.append(conclusion)
    if error_msg is not None:
        sets.append("error_msg = %s")
        params.append(error_msg)
    if not sets:
        return
    params.append(task_id)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE task SET {', '.join(sets)} WHERE id = %s", params)
    finally:
        conn.close()


def get_task(task_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM task WHERE id = %s", (task_id,))
            return cur.fetchone()
    finally:
        conn.close()


def get_document(document_id: int):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM document WHERE id = %s", (document_id,))
            return cur.fetchone()
    finally:
        conn.close()


def list_tasks(limit: int = 50):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT t.id, t.task_no, d.file_name, t.status, t.conclusion, t.created_at
                FROM task t JOIN document d ON t.document_id = d.id
                ORDER BY t.id DESC LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ============ 实体 / 风险 / 报告 ============

def save_entity(task_id: int, entity) -> None:
    """保存实体（18 字段映射到 entity 表）。"""
    d = entity.model_dump(mode="json")
    guarantors = json.dumps(d["guarantors"], ensure_ascii=False) if d["guarantors"] else None
    has_overdue = None if d["has_overdue"] is None else (1 if d["has_overdue"] else 0)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO entity (task_id, company_name, credit_code, credit_amount, currency,
                    credit_term_months, interest_rate, total_liability, debt_ratio,
                    accounts_receivable, external_guarantee, due_date, guarantors, guarantee_type,
                    has_overdue, overdue_detail, litigation, main_business, legal_representative)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    task_id, d["company_name"], d["credit_code"], d["credit_amount"], d["currency"],
                    d["credit_term_months"], d["interest_rate"], d["total_liability"], d["debt_ratio"],
                    d["accounts_receivable"], d["external_guarantee"], d["due_date"], guarantors, d["guarantee_type"],
                    has_overdue, d["overdue_detail"], d["litigation"], d["main_business"], d["legal_representative"],
                ),
            )
    finally:
        conn.close()


def save_risks(task_id: int, risks: list) -> None:
    """批量保存风险点。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for r in risks:
                cur.execute(
                    """
                    INSERT INTO risk (task_id, risk_type, risk_level, description, evidence, suggestion, engine)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (task_id, r.risk_type.value, r.risk_level.value, r.description, r.evidence, r.suggestion, r.engine),
                )
    finally:
        conn.close()


def save_report(task_id: int, report, is_final: bool = False) -> None:
    """保存报告（存 JSON 快照 + 关键字段）。"""
    report_json = json.dumps(report.model_dump(mode="json"), ensure_ascii=False)
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO report (task_id, is_final, conclusion, risk_summary, report_json)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (task_id, 1 if is_final else 0, report.conclusion, report.risk_summary, report_json),
            )
    finally:
        conn.close()


def get_report(task_id: int, is_final: bool = False):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM report WHERE task_id = %s AND is_final = %s ORDER BY id DESC LIMIT 1",
                (task_id, 1 if is_final else 0),
            )
            return cur.fetchone()
    finally:
        conn.close()


def get_stats():
    """简单统计：任务数 / 风险数 / 高风险数。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM task")
            total_tasks = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM risk")
            total_risks = cur.fetchone()["n"]
            cur.execute("SELECT COUNT(*) AS n FROM risk WHERE risk_level = '高'")
            high_risks = cur.fetchone()["n"]
        return {"total_tasks": total_tasks, "total_risks": total_risks, "high_risks": high_risks}
    finally:
        conn.close()


# ============ 人工复核相关 ============

def get_or_create_user(username: str) -> int:
    """按用户名取用户 id，不存在则创建（简单版，无完整鉴权）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM user WHERE username = %s", (username,))
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute(
                "INSERT INTO user (username, password_hash, role) VALUES (%s, 'dummy', 'reviewer')",
                (username,),
            )
            return cur.lastrowid
    finally:
        conn.close()


def get_risks(task_id: int) -> list:
    """读取任务的风险点，重建为 RiskPoint 对象列表。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM risk WHERE task_id = %s ORDER BY id", (task_id,))
            rows = cur.fetchall()
        return [
            RiskPoint(
                risk_type=RiskType(r["risk_type"]),
                risk_level=RiskLevel(r["risk_level"]),
                description=r["description"],
                evidence=r["evidence"],
                suggestion=r["suggestion"],
                engine=r["engine"],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_entity(task_id: int):
    """读取任务的实体，重建为 FinancialEntity（DECIMAL→float、TINYINT→bool、JSON→list）。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM entity WHERE task_id = %s", (task_id,))
            row = cur.fetchone()
        if not row:
            return None

        def _f(key):  # 数值字段：None 或 float
            v = row.get(key)
            return float(v) if v is not None else None

        def _b(key):  # 布尔字段：None/False/True
            v = row.get(key)
            return None if v is None else bool(v)

        def _l(key):  # 列表字段：JSON 字符串 → list
            v = row.get(key)
            return json.loads(v) if v else []

        return FinancialEntity(
            company_name=row["company_name"],
            credit_code=row.get("credit_code"),
            credit_amount=_f("credit_amount"),
            currency=row["currency"],
            credit_term_months=row.get("credit_term_months"),
            interest_rate=_f("interest_rate"),
            total_liability=_f("total_liability"),
            debt_ratio=_f("debt_ratio"),
            accounts_receivable=_f("accounts_receivable"),
            external_guarantee=_f("external_guarantee"),
            due_date=row.get("due_date"),
            guarantors=_l("guarantors"),
            guarantee_type=row.get("guarantee_type"),
            has_overdue=_b("has_overdue"),
            overdue_detail=row.get("overdue_detail"),
            litigation=row.get("litigation"),
            main_business=row.get("main_business"),
            legal_representative=row.get("legal_representative"),
        )
    finally:
        conn.close()


def save_review_log(task_id: int, reviewer_id: int, entry: dict) -> None:
    """保存一条复核日志。"""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_log (task_id, reviewer_id, action, field_name, old_value, new_value, remark)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """,
                (task_id, reviewer_id, entry.get("action"), entry.get("field_name"),
                 entry.get("old_value"), entry.get("new_value"), entry.get("remark")),
            )
    finally:
        conn.close()
