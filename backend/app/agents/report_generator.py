"""标准化报告生成 Agent（流水线第 4 步）。

职责：汇总实体、风险点、合规建议，生成标准化审查报告。
输入：RiskState 全部字段（entities / risks / task_id / file_name）
输出：写入 RiskState.report（Report 模型）
依赖：templates/report.md.j2（Jinja2 模板，供 render_report_markdown 渲染）
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.core.state import STATUS_REPORTING, RiskState
from app.models import Report, RiskLevel

# Jinja2 模板目录：backend/templates（本文件在 backend/app/agents/，上三级是 backend）
TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def _decide_conclusion(risks: list) -> str:
    """根据风险点定初审结论：
    - 无风险 → 通过
    - 有高风险 → 不通过
    - 只有中/低风险 → 需人工复核
    """
    if not risks:
        return "通过"
    if any(r.risk_level == RiskLevel.HIGH for r in risks):
        return "不通过"
    return "需人工复核"


def _summarize(risks: list) -> str:
    """生成风险汇总段落（规则版，不调 LLM，确定性输出）。"""
    if not risks:
        return "未识别到合规风险。"
    high = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)
    medium = sum(1 for r in risks if r.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for r in risks if r.risk_level == RiskLevel.LOW)
    types = {r.risk_type.value for r in risks}
    return f"共识别 {len(risks)} 个风险点（高 {high} / 中 {medium} / 低 {low}），涉及：{'、'.join(types)}。"


def build_report(task_id: str, file_name: str, entities, risks: list) -> Report:
    """根据输入构建 Report（供报告生成 Agent 与人工复核共用）。"""
    return Report(
        task_id=task_id,
        file_name=file_name,
        conclusion=_decide_conclusion(risks),
        entities=entities,
        risks=risks,
        risk_summary=_summarize(risks),
        suggestions=[r.suggestion for r in risks],
    )


def generate_report(state: RiskState) -> dict:
    """节点④：汇总实体、风险点，生成标准化审查报告。"""
    report = build_report(
        state["task_id"],
        state["file_name"],
        state.get("entities"),
        state.get("risks") or [],
    )
    return {"report": report, "status": STATUS_REPORTING}


def render_report_markdown(report: Report) -> str:
    """用 Jinja2 模板把报告渲染成 Markdown（供预览/导出）。"""
    template = _env.get_template("report.md.j2")
    return template.render(report=report)


# ===== PDF 导出 =====

# 中文字体候选（跨平台：Windows / Linux），部署到 Linux 服务器时需装对应字体
_PDF_FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",                             # Windows 黑体
    "C:/Windows/Fonts/msyh.ttc",                               # Windows 微软雅黑
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux Noto CJK
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",          # Linux 文泉驿
    "/usr/share/fonts/truetype/arphic/uming.ttc",              # Linux AR PL UMing
]
_pdf_font_registered = False


def _find_font() -> str:
    """查找系统中第一个可用的中文字体。"""
    import os
    for path in _PDF_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return _PDF_FONT_CANDIDATES[0]


def _overdue_text(v) -> str:
    return "未提及" if v is None else ("是" if v else "否")


def render_report_pdf(report: Report) -> bytes:
    """用 reportlab 把报告渲染成 PDF 字节流（供下载导出）。"""
    import io

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    global _pdf_font_registered
    if not _pdf_font_registered:
        pdfmetrics.registerFont(TTFont("Hei", _find_font(), subfontIndex=0))
        _pdf_font_registered = True

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )

    st_title = ParagraphStyle("t", fontName="Hei", fontSize=18, leading=24, alignment=1, spaceAfter=14)
    st_h = ParagraphStyle("h", fontName="Hei", fontSize=13, leading=18, spaceBefore=12, spaceAfter=8,
                          textColor=colors.HexColor("#409eff"))
    st_body = ParagraphStyle("b", fontName="Hei", fontSize=10, leading=16)
    st_risk = ParagraphStyle("r", fontName="Hei", fontSize=10, leading=15, spaceAfter=2)

    story = []
    story.append(Paragraph("金融文本风控审查报告", st_title))
    story.append(Paragraph(f"任务编号：{report.task_id}", st_body))
    story.append(Paragraph(f"审查文档：{report.file_name}", st_body))
    story.append(Paragraph(f"初审结论：<b>{report.conclusion}</b>", st_body))
    story.append(Spacer(1, 5 * mm))

    # 风险汇总
    story.append(Paragraph("一、风险汇总", st_h))
    story.append(Paragraph(report.risk_summary, st_body))

    # 实体信息
    story.append(Paragraph("二、实体信息", st_h))
    if report.entities:
        e = report.entities
        rows = [
            ["企业名称", e.company_name or "—", "授信金额", f"{e.credit_amount or '—'} 万元"],
            ["币种", e.currency or "—", "授信期限", f"{e.credit_term_months or '—'} 个月"],
            ["年化利率", f"{e.interest_rate or '—'}%", "资产负债率", f"{e.debt_ratio or '—'}%"],
            ["负债总额", f"{e.total_liability or '—'} 万元", "担保方式", e.guarantee_type or "—"],
            ["担保主体", "、".join(e.guarantors) if e.guarantors else "—", "是否逾期", _overdue_text(e.has_overdue)],
        ]
        table = Table(rows, colWidths=[28 * mm, 57 * mm, 28 * mm, 57 * mm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Hei"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5f7fa")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f5f7fa")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("未抽取到实体信息", st_body))

    # 风险点
    story.append(Paragraph(f"三、风险点（{len(report.risks)} 个）", st_h))
    if report.risks:
        for i, r in enumerate(report.risks, 1):
            src = "规则" if r.engine == "rule" else "语义"
            story.append(Paragraph(f"{i}. 【{r.risk_level.value}】{r.risk_type.value}（来源：{src}）", st_risk))
            story.append(Paragraph(f"　　描述：{r.description}", st_body))
            story.append(Paragraph(f"　　原文依据：{r.evidence}", st_body))
            story.append(Paragraph(f"　　整改建议：{r.suggestion}", st_body))
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("未识别到合规风险。", st_body))

    # 建议
    if report.suggestions:
        story.append(Paragraph("四、综合合规建议", st_h))
        for i, s in enumerate(report.suggestions, 1):
            story.append(Paragraph(f"{i}. {s}", st_body))

    doc.build(story)
    return buf.getvalue()
