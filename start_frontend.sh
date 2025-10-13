#!/bin/bash

# RAG评测平台 - 前端启动脚本

echo "============================================"
echo "启动RAG评测平台前端界面"
echo "============================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 启动前端
echo "启动Streamlit前端..."
streamlit run frontend/app.py --server.port 8501

