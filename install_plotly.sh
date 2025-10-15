#!/bin/bash
# 安装plotly用于统计页面可视化

echo "正在安装plotly..."

# 方法1: 使用清华镜像源
pip install plotly -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果方法1失败，尝试方法2: 使用阿里云镜像
if [ $? -ne 0 ]; then
    echo "尝试阿里云镜像..."
    pip install plotly -i https://mirrors.aliyun.com/pypi/simple/
fi

# 如果方法2失败，尝试方法3: 使用豆瓣镜像
if [ $? -ne 0 ]; then
    echo "尝试豆瓣镜像..."
    pip install plotly -i https://pypi.douban.com/simple/
fi

# 验证安装
python -c "import plotly; print(f'✅ Plotly安装成功! 版本: {plotly.__version__}')" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Plotly安装成功！"
else
    echo "❌ Plotly安装失败，请手动执行:"
    echo "pip install plotly"
fi

