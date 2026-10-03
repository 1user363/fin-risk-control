"""FAISS 向量知识库服务。

职责：加载 knowledge_base/ 下的监管条例/合规准则/历史案例，embedding 后建 FAISS 索引，
提供 search(query, top_k) 相似度检索，供风险识别 Agent 辅助判定合规边界。

为什么用向量检索而非关键词匹配：能识别「保本」和「稳赚不赔」这类词不同但语义相同的表述。
"""

from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from app.config import settings

KB_DIR = Path(__file__).resolve().parents[2] / "knowledge_base"  # backend/knowledge_base

_embeddings = None
_index = None  # 缓存的 FAISS 索引


def get_embeddings():
    """懒加载 embedding 模型（走硅基流动）。"""
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.EMBEDDING_BASE_URL,
            api_key=settings.EMBEDDING_API_KEY,
        )
    return _embeddings


def load_corpus() -> list[str]:
    """从 knowledge_base/ 读取所有 .txt/.md 语料，按行拆成条目（跳过 README 文档）。"""
    texts = []
    for p in sorted(KB_DIR.glob("*")):
        if p.suffix.lower() not in {".txt", ".md"}:
            continue
        if p.stem.lower().startswith("readme"):  # 跳过 README 说明文档，不作为语料
            continue
        content = p.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                texts.append(line)
    return texts


def build_index() -> FAISS:
    """构建（或加载缓存）FAISS 索引。"""
    global _index
    if _index is None:
        texts = load_corpus()
        if not texts:
            raise ValueError("知识库为空：请在 knowledge_base/ 下放 .txt/.md 语料")
        _index = FAISS.from_texts(texts, get_embeddings())
    return _index


def search(query: str, k: int = 3) -> list[str]:
    """检索与 query 语义最相近的 k 条语料，返回文本列表。"""
    index = build_index()
    docs = index.similarity_search(query, k=k)
    return [d.page_content for d in docs]
