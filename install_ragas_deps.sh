#!/bin/bash
# 安装Ragas评估所需的依赖

echo "🚀 安装Ragas评估依赖..."
echo "======================================"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo "检测到虚拟环境，激活中..."
    source venv/bin/activate
fi

# 安装langchain-openai
echo ""
echo "📦 安装 langchain-openai..."
pip install langchain-openai==0.0.5

# 验证安装
echo ""
echo "✅ 验证安装..."
python3 -c "from langchain_openai import ChatOpenAI, OpenAIEmbeddings; print('langchain-openai: OK')" && \
python3 -c "from ragas import evaluate; print('ragas: OK')" && \
echo "" && \
echo "🎉 所有依赖安装成功！" && \
echo "" && \
echo "下一步:" && \
echo "1. 重启后端服务: cd backend && python main.py" && \
echo "2. 重启前端服务: streamlit run frontend/app.py" && \
echo "3. 进行RAG评估，查看Ragas评分"


