# 🚀 快速开始指南

## 5分钟上手RAG评测平台

### 1️⃣ 准备工作（1分钟）

```bash
# 进入项目目录
cd /Users/xiniuyiliao/Desktop/XNProject/AIKnowledgeBase/agenticRAG/rag-all-techniques-master/rag_all_app

# 检查Python版本（需要3.8+）
python3 --version

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ 安装依赖（2分钟）

```bash
# 安装所有依赖
pip install -r requirements.txt
```

### 3️⃣ 配置环境（1分钟）

编辑 `.env` 文件，配置您的API服务：

```bash
# 必须配置的项
LLM_BASE_URL=http://10.10.50.150:8712/v1
LLM_API_KEY=your_api_key

EMBEDDING_BASE_URL=http://10.10.50.150:8998/v1
EMBEDDING_API_KEY=your_embedding_key
```

### 4️⃣ 启动服务（1分钟）

#### 方式A：一键启动（推荐）

```bash
./start_all.sh
```

#### 方式B：分别启动

```bash
# 终端1 - 后端
./start_backend.sh

# 终端2 - 前端
./start_frontend.sh
```

### 5️⃣ 开始使用

访问 **http://localhost:8501** 即可看到界面！

## 📝 第一次使用流程

### Step 1: 上传文档
1. 点击左侧"上传文档"
2. 选择一个PDF或TXT文件
3. 点击"上传并处理"
4. 等待处理完成（会看到成功提示）

### Step 2: 配置RAG
1. 勾选刚上传的文档
2. 在"RAG配置"中保持默认（Simple RAG）
3. 可选：调整检索参数（top_k、chunk_size等）

### Step 3: 提问
1. 在中间对话窗口输入问题
2. 例如："这篇文档主要讲了什么？"
3. 回车提交

### Step 4: 查看结果
1. 中间窗口显示主答案
2. 右侧面板显示详细信息：
   - 检索到的文档片段
   - 相似度分数
   - 执行时间

### Step 5: 评分（可选）
1. 在右侧面板对答案评分
2. 准确性、相关性、流畅性、完整性
3. 点击"提交评分"

## 🎯 测试示例

### 示例1：基础问答

**上传文档**: `data/AI_Information.pdf`（如果有）

**问题**: 
```
什么是人工智能？
```

**预期**: 系统会检索相关段落并生成回答

### 示例2：对比多个RAG技术

1. 选择多个RAG技术（未来添加后）
2. 提出同一个问题
3. 在右侧标签页查看不同技术的结果
4. 对比执行时间和答案质量

### 示例3：查看统计

1. 多次提问并评分
2. 滚动到右侧底部
3. 查看"统计对比"图表

## ⚠️ 常见问题

### 问题1: 启动失败
```bash
# 检查端口是否被占用
lsof -i :8000  # 后端端口
lsof -i :8501  # 前端端口

# 如果被占用，杀掉进程或修改端口
```

### 问题2: 依赖安装失败
```bash
# 使用清华源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题3: 连接后端失败
```bash
# 确认后端已启动
curl http://localhost:8000/health

# 查看后端日志
tail -f logs/app_*.log
```

### 问题4: Embedding失败
- 检查EMBEDDING_BASE_URL是否可访问
- 检查EMBEDDING_API_KEY是否正确
- 测试embedding服务：
```bash
curl --location 'http://10.10.50.150:8998/v1/embeddings' \
  --header "Authorization: Bearer your_key" \
  --header 'Content-Type: application/json' \
  --data '{"model": "bge-large-zh-v1.5", "input": ["测试"]}'
```

## 🔧 开发模式

### 实时调试后端

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 实时调试前端

```bash
streamlit run frontend/app.py --server.runOnSave true
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/app_*.log

# 查看最近100行
tail -n 100 logs/app_*.log
```

## 📚 下一步

1. **阅读完整文档**: 查看 `README.md`
2. **添加更多文档**: 上传不同类型的文档
3. **尝试不同配置**: 调整RAG参数观察效果
4. **查看API文档**: http://localhost:8000/docs
5. **贡献代码**: 添加新的RAG技术

## 💡 提示

- 建议第一次使用时上传较小的文档（<5MB）
- 问题尽量具体，这样检索效果更好
- 可以查看检索到的文档片段，了解答案来源
- 多次使用后查看统计图表，分析RAG性能

---

**祝使用愉快！有问题请查看README或提Issue** 🎉

