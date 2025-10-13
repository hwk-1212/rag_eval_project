import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api import api_router
from backend.models import init_db
from backend.utils.logger import setup_logger
from backend.config import settings

# 设置日志
setup_logger()

# 创建FastAPI应用
app = FastAPI(
    title="RAG评测对比平台",
    description="支持多种RAG技术的评测与对比系统",
    version="1.0.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("=" * 50)
    logger.info("RAG评测对比平台启动中...")
    logger.info("=" * 50)
    
    # 初始化数据库
    init_db()
    
    logger.info(f"后端服务启动在: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    logger.info(f"API文档: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("RAG评测对比平台关闭")


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "RAG评测对比平台 API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )

