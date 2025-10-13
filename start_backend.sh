#!/bin/bash

# RAG评测平台 - 后端启动脚本

echo "============================================"
echo "启动RAG评测平台后端服务"
echo "============================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "未找到虚拟环境，正在创建..."
    python3 -m venv venv
    echo "虚拟环境创建完成"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
# source venv/bin/activate

# # 安装依赖
# echo "检查依赖..."
# pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 启动后端
echo "启动FastAPI后端服务..."
cd backend
python main.py

