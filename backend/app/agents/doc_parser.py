"""文档解析 Agent（流水线第 1 步）。

职责：把上传的 PDF / 图片 / 扫描件解析成纯净文本。
输入：RiskState.file_path（文档本地路径）
输出：写入 RiskState.doc_text（清洗后的纯文本）
依赖：services/ocr.py
"""

from app.core.state import STATUS_PARSING, RiskState
from app.services import ocr


def parse_document(state: RiskState) -> dict:
    """节点①：调用 OCR 服务解析文档，产出 doc_text。

    只返回自己负责的字段（doc_text + status），其余字段由 LangGraph 自动合并。
    """
    doc_text = ocr.parse(state["file_path"])
    return {"doc_text": doc_text, "status": STATUS_PARSING}
