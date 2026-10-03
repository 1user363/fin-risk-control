"""配置中心。

职责：用 python-dotenv 从 backend/.env 读取配置，暴露全局 settings 单例。
用法：`from app.config import settings`，然后 settings.LLM_MODEL 等。

注意：.env 路径用 Path(__file__) 定位，保证无论从哪个目录运行都能找到。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env（本文件在 backend/app/config.py，上两级是 backend）
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings:
    """全局配置（从 .env 读取，类属性在 import 时求值一次）。"""

    # ===== LLM（OpenAI 兼容协议，可切 DeepSeek / Qwen / GLM） =====
    LLM_BASE_URL: str = _get("LLM_BASE_URL", "https://api.deepseek.com/v1")
    LLM_API_KEY: str = _get("LLM_API_KEY", "")
    LLM_MODEL: str = _get("LLM_MODEL", "deepseek-chat")

    # ===== Embedding（向量模型，走硅基流动，DeepSeek 官方无 embedding） =====
    EMBEDDING_BASE_URL: str = _get("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
    EMBEDDING_API_KEY: str = _get("EMBEDDING_API_KEY", "")
    EMBEDDING_MODEL: str = _get("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-4B")

    # ===== MySQL =====
    MYSQL_HOST: str = _get("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(_get("MYSQL_PORT", "3306"))
    MYSQL_USER: str = _get("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = _get("MYSQL_PASSWORD", "")
    MYSQL_DB: str = _get("MYSQL_DB", "risk_control")


settings = Settings()
