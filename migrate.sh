#!/bin/bash
# 数据库迁移脚本

echo "======================================"
echo "RAG评测平台 - 数据库迁移工具 V1.8.7"
echo "======================================"

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查数据库文件是否存在
DB_FILE="backend/data/rag_eval.db"
if [ ! -f "$DB_FILE" ]; then
    echo "❌ 错误: 数据库文件不存在: $DB_FILE"
    exit 1
fi

echo "📦 数据库位置: $DB_FILE"
echo ""

# 使用SQLite命令执行迁移
echo "🔄 开始迁移..."
echo ""

# 添加 faithfulness_score 字段
echo "添加 faithfulness_score 字段..."
sqlite3 "$DB_FILE" "ALTER TABLE evaluations ADD COLUMN faithfulness_score REAL;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ faithfulness_score 添加成功"
else
    echo "⚠️  faithfulness_score 字段可能已存在（跳过）"
fi

# 添加 coherence_score 字段
echo "添加 coherence_score 字段..."
sqlite3 "$DB_FILE" "ALTER TABLE evaluations ADD COLUMN coherence_score REAL;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ coherence_score 添加成功"
else
    echo "⚠️  coherence_score 字段可能已存在（跳过）"
fi

# 添加 conciseness_score 字段
echo "添加 conciseness_score 字段..."
sqlite3 "$DB_FILE" "ALTER TABLE evaluations ADD COLUMN conciseness_score REAL;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ conciseness_score 添加成功"
else
    echo "⚠️  conciseness_score 字段可能已存在（跳过）"
fi

echo ""
echo "======================================"
echo "验证迁移结果"
echo "======================================"

# 查看表结构
echo ""
echo "evaluations表当前字段:"
sqlite3 "$DB_FILE" "PRAGMA table_info(evaluations);" | while IFS='|' read -r cid name type notnull dflt_value pk; do
    echo "  - $name ($type)"
done

echo ""
echo "======================================"
echo "✅ 数据库迁移完成！"
echo "======================================"
echo ""
echo "后续步骤:"
echo "1. 重启后端服务"
echo "2. 重启前端服务"
echo "3. 测试评估功能"
echo ""

