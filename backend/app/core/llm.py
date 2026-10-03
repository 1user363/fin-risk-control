"""LLM 客户端封装 —— OpenAI 兼容协议统一入口。

职责：从 .env 读取 base_url / api_key / model，可切换 DeepSeek / Qwen / GLM。
提供：
- get_llm()         —— 普通对话模型
- structured_llm()  —— 带强结构化输出约束的模型（with_structured_output）
"""

from langchain_openai import ChatOpenAI

from app.config import settings

_llm = None


def get_llm() -> ChatOpenAI:
    """懒加载 ChatOpenAI 客户端（只初始化一次）。"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            temperature=0,  # 抽取/判定任务要稳定，温度设 0 减少随机性
        )
    return _llm


def structured_llm(schema):
    """返回带强结构化输出约束的可调用对象。

    用法：structured_llm(FinancialEntity).invoke(text) -> FinancialEntity
    底层是 function calling：Pydantic 模型 → JSON Schema → 约束 LLM 输出合法 JSON。

    注意 method="function_calling"：DeepSeek 官方不支持 json_schema 响应格式，
    必须显式用函数调用方式（否则报 "response_format type is unavailable"）。
    """
    return get_llm().with_structured_output(schema, method="function_calling")
