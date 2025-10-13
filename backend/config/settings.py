from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """全局配置"""
    
    # 项目基础路径
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # LLM配置
    LLM_BASE_URL: str = "http://10.10.50.150:8712/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "Qwen3-4B-Instruct-2507"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # Embedding配置
    EMBEDDING_BASE_URL: str = "http://10.10.50.150:8997/v1"
    EMBEDDING_API_KEY: str = "sk-hvQkeyj7IutpUure4632155dCeB440CcBf8eBc93014e8998"
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    
    # Reranker配置
    RERANKER_BASE_URL: str = "http://10.10.50.150:8996"
    RERANKER_API_KEY: str = "sk-hvQkeyj7IutpUure4632155dCeB440CcBf8eBc93014e8996"
    RERANKER_MODEL: str = "bge-reranker-v2-m3"
    
    # 数据库配置
    SQLITE_DB_PATH: str = "./data/rag_eval.db"
    MILVUS_URI: str = "./data/vector_db/milvus.db"
    
    # 服务器配置
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_PORT: int = 8501
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "./logs"
    
    # 文件上传配置
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: set = {".pdf", ".txt", ".docx", ".md"}
    
    # RAG配置
    DEFAULT_CHUNK_SIZE: int = 500
    DEFAULT_CHUNK_OVERLAP: int = 100
    DEFAULT_TOP_K: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# 确保必要的目录存在
for directory in [
    settings.UPLOAD_DIR,
    settings.LOG_PATH,
    Path(settings.SQLITE_DB_PATH).parent,
    Path(settings.MILVUS_URI).parent,
]:
    Path(directory).mkdir(parents=True, exist_ok=True)

