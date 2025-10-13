from loguru import logger
import sys
from pathlib import Path
from backend.config import settings


def setup_logger():
    """配置全局日志"""
    
    # 移除默认handler
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    
    # 添加文件输出
    log_path = Path(settings.LOG_PATH)
    log_path.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_path / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level=settings.LOG_LEVEL,
        rotation="00:00",  # 每天轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩
        encoding="utf-8",
    )
    
    logger.info("日志系统初始化完成")

