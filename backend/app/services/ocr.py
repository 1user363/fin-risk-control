"""OCR 与文档解析服务。

职责：把 PDF / 图片 / 扫描件解析成纯净文本。
- 有文本层的 PDF：PyMuPDF 直接提取（快、准、无需 OCR）
- 扫描件 / 图片：RapidOCR 光学识别
- 统一输出：清洗后的纯净文本（去控制字符 / 空行 / 页码）

入口：parse(path) -> str
"""

import os
from typing import List

# 支持的图片扩展名
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# RapidOCR 引擎懒加载（ONNX 模型加载慢，只在真正需要 OCR 时才初始化，且只初始化一次）
_ocr_engine = None


class DocParseError(Exception):
    """文档解析失败（文件不存在 / 不支持的类型 / 解析异常）。"""


def _get_ocr_engine():
    """懒加载并缓存 RapidOCR 引擎，避免每次调用重复加载 ONNX 模型。"""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR

        _ocr_engine = RapidOCR()
    return _ocr_engine


def _extract_pdf_text(path: str) -> str:
    """提取「有文本层」的 PDF（用 PyMuPDF）。"""
    import pymupdf

    doc = pymupdf.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _ocr_image_bytes(img_bytes: bytes) -> str:
    """对图片字节流做 OCR，返回识别文本。"""
    result, _ = _get_ocr_engine()(img_bytes)
    if not result:
        return ""
    # result 每条是 [四点坐标, 文本, 置信度]，取第 1 个元素（文本）
    return "\n".join(item[1] for item in result)


def _ocr_pdf(path: str) -> str:
    """扫描件 PDF：逐页渲染成图片再 OCR。"""
    import pymupdf

    doc = pymupdf.open(path)
    parts: List[str] = []
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=200)  # 200 DPI 渲染成图片
            parts.append(_ocr_image_bytes(pix.tobytes("png")))
    finally:
        doc.close()
    return "\n".join(parts)


def _clean_text(text: str) -> str:
    """基础清洗：去控制字符、去空行、去纯页码短行。

    说明：清洗策略可后续扩展（去水印、合并中文断行等），先做最必要的。
    """
    import re

    # 去掉控制字符（保留换行和制表符）
    text = "".join(ch for ch in text if ch in "\n\t" or ch >= " ")
    lines: List[str] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 去掉纯数字短行（扫描件页眉页脚的页码）
        if re.fullmatch(r"\d{1,4}", line):
            continue
        lines.append(line)
    return "\n".join(lines)


def parse(path: str) -> str:
    """解析文档，返回清洗后的纯净文本。

    Args:
        path: 文档本地路径

    Returns:
        纯净文本字符串

    Raises:
        DocParseError: 文件不存在或类型不支持
    """
    if not os.path.exists(path):
        raise DocParseError(f"文件不存在: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".pdf":
        text = _extract_pdf_text(path)
        # 文本层为空（或极少），判定为扫描件 → 走 OCR
        if len(text.strip()) < 10:
            text = _ocr_pdf(path)
    elif ext in IMAGE_EXTS:
        with open(path, "rb") as f:
            text = _ocr_image_bytes(f.read())
    else:
        raise DocParseError(f"暂不支持的文件类型: {ext}（当前支持 PDF 和图片）")

    return _clean_text(text)
