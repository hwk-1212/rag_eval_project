#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移执行脚本
快速执行数据库迁移
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.migrations.migrate_v1_8_7 import migrate
from loguru import logger


def main():
    """主函数"""
    logger.info("🚀 开始执行数据库迁移...")
    logger.info("-" * 60)
    
    # 执行迁移
    success = migrate()
    
    logger.info("-" * 60)
    
    if success:
        logger.success("✅ 数据库迁移成功完成！")
        logger.info("\n后续步骤:")
        logger.info("1. 重启后端服务: cd backend && python main.py")
        logger.info("2. 重启前端服务: streamlit run frontend/app.py")
        logger.info("3. 测试评估功能，确认新字段正常保存")
        return 0
    else:
        logger.error("❌ 数据库迁移失败！")
        logger.info("\n故障排除:")
        logger.info("1. 检查数据库文件是否存在: backend/data/rag_eval.db")
        logger.info("2. 确认数据库没有被其他进程占用")
        logger.info("3. 查看上方的错误信息")
        logger.info("\n如果问题依然存在，可以考虑:")
        logger.info("- 备份现有数据")
        logger.info("- 删除数据库文件重新开始: rm backend/data/rag_eval.db")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

