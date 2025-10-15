# -*- coding: utf-8 -*-
"""
数据库迁移脚本 V1.8.7
添加评估表的新字段：faithfulness_score, coherence_score, conciseness_score
"""
import sqlite3
import os
from pathlib import Path
from loguru import logger


def get_db_path():
    """获取数据库路径"""
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / "data" / "rag_eval.db"
    return str(db_path)


def check_column_exists(cursor, table_name, column_name):
    """检查列是否已存在"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    """执行数据库迁移"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        logger.error(f"数据库文件不存在: {db_path}")
        return False
    
    logger.info(f"开始迁移数据库: {db_path}")
    
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 备份原有数据（可选，但推荐）
        logger.info("备份evaluations表数据...")
        cursor.execute("SELECT COUNT(*) FROM evaluations")
        count = cursor.fetchone()[0]
        logger.info(f"当前evaluations表有 {count} 条记录")
        
        # 检查并添加 faithfulness_score 字段
        if not check_column_exists(cursor, "evaluations", "faithfulness_score"):
            logger.info("添加 faithfulness_score 字段...")
            cursor.execute("""
                ALTER TABLE evaluations 
                ADD COLUMN faithfulness_score REAL
            """)
            logger.success("✅ faithfulness_score 字段添加成功")
        else:
            logger.info("faithfulness_score 字段已存在，跳过")
        
        # 检查并添加 coherence_score 字段
        if not check_column_exists(cursor, "evaluations", "coherence_score"):
            logger.info("添加 coherence_score 字段...")
            cursor.execute("""
                ALTER TABLE evaluations 
                ADD COLUMN coherence_score REAL
            """)
            logger.success("✅ coherence_score 字段添加成功")
        else:
            logger.info("coherence_score 字段已存在，跳过")
        
        # 检查并添加 conciseness_score 字段
        if not check_column_exists(cursor, "evaluations", "conciseness_score"):
            logger.info("添加 conciseness_score 字段...")
            cursor.execute("""
                ALTER TABLE evaluations 
                ADD COLUMN conciseness_score REAL
            """)
            logger.success("✅ conciseness_score 字段添加成功")
        else:
            logger.info("conciseness_score 字段已存在，跳过")
        
        # 提交更改
        conn.commit()
        
        # 验证迁移结果
        logger.info("验证迁移结果...")
        cursor.execute("PRAGMA table_info(evaluations)")
        columns = cursor.fetchall()
        
        logger.info("evaluations表当前字段:")
        for col in columns:
            logger.info(f"  - {col[1]} ({col[2]})")
        
        # 验证新字段是否存在
        column_names = [col[1] for col in columns]
        required_fields = ["faithfulness_score", "coherence_score", "conciseness_score"]
        
        all_exists = all(field in column_names for field in required_fields)
        
        if all_exists:
            logger.success("🎉 数据库迁移成功完成！")
            logger.info(f"原有数据保留: {count} 条记录")
            return True
        else:
            missing = [f for f in required_fields if f not in column_names]
            logger.error(f"迁移失败，缺少字段: {missing}")
            return False
            
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("RAG评测平台 - 数据库迁移工具 V1.8.7")
    logger.info("=" * 60)
    
    success = migrate()
    
    if success:
        logger.success("\n✅ 迁移完成！现在可以重启后端服务。")
        logger.info("\n使用以下命令重启:")
        logger.info("  cd backend && python main.py")
    else:
        logger.error("\n❌ 迁移失败！请检查错误信息。")

