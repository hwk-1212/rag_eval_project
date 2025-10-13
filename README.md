# 🤖 RAG评测对比平台 V1.2

一个支持多种RAG技术的评测与对比系统，让您能够直观地比较不同RAG方案的效果。

## 🌟 最新特性

### V1.3 - 批量自动评估与统计对比 (NEW! 2025-10-13)
- 🤖 **LLM自动评分**: 6维度智能评分（相关性、忠实度、连贯性、流畅度、简洁性、综合）
- 📊 **Ragas集成**: 标准化RAG评估指标（Faithfulness、Answer Relevancy，无需标准答案）
- ⚡ **批量评估**: 一键评估所有选中的RAG技术，实时进度显示
- 📈 **统计对比**: 详细对比表格 + 可视化图表 + 智能推荐
- 💾 **自动保存**: 评估结果自动持久化到数据库
- 🎯 **检索质量评估**: 自动评估检索精确度和上下文相关性
- ⚙️ **评估配置**: 侧边栏独立配置，支持开关LLM和Ragas评估

### V1.2 - 高级RAG技术
- ✨ **Query Transformation RAG**: 查询重写、回退提示、子查询分解
- ✨ **Adaptive RAG**: 智能识别查询类型，自动选择最佳策略
- ✨ **Self RAG**: 6个反思点质量控制，确保答案可靠性
- 🎯 **8个RAG技术**: 从基础到高级，全面覆盖主流技术

## 📋 核心特性

- ✅ **多文档支持**: 支持PDF、TXT、MD、DOCX等多种格式
- ✅ **多RAG技术对比**: 同时运行多个RAG技术，并列展示结果
- ✅ **实时问答**: 对话式交互界面，即时获取答案
- ✅ **详细溯源**: 展示检索到的文档片段和相似度分数
- ✅ **评分系统**: 支持人工多维度评分
- ✅ **统计分析**: 自动生成各RAG技术的性能对比
- ✅ **灵活配置**: 可调整检索参数、LLM参数等
- ✅ **智能路由**: 根据问题类型自动优化策略
- ✅ **质量保证**: 多重评估确保答案准确性

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG评测对比平台                           │
├─────────────────────────────────────────────────────────────┤
│  前端 (Streamlit)                                            │
│  ┌────────────┬──────────────┬─────────────────────────┐   │
│  │ 文件管理   │  对话窗口    │  RAG结果对比            │   │
│  │ RAG配置    │  历史记录    │  评分统计               │   │
│  └────────────┴──────────────┴─────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  后端 (FastAPI)                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  API层: Documents | QA | Evaluation                │    │
│  ├────────────────────────────────────────────────────┤    │
│  │  业务层: DocumentLoader | VectorStore | RAGChain   │    │
│  ├────────────────────────────────────────────────────┤    │
│  │  RAG技术: Simple RAG | Reranker | Fusion | ...     │    │
│  └────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  数据层                                                      │
│  ┌──────────────┬──────────────────────────────────────┐  │
│  │ SQLite       │ Milvus Lite (向量数据库)              │  │
│  │ (元数据)     │ (文档向量)                            │  │
│  └──────────────┴──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- 10GB+ 磁盘空间
- 可访问的LLM和Embedding API

### 2. 安装依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置您的LLM和Embedding服务：

```ini
# LLM配置
LLM_BASE_URL=http://your-llm-service:8712/v1
LLM_API_KEY=your_api_key
LLM_MODEL=Qwen3-4B-Instruct-2507

# Embedding配置
EMBEDDING_BASE_URL=http://your-embedding-service:8998/v1
EMBEDDING_API_KEY=your_embedding_key
EMBEDDING_MODEL=bge-large-zh-v1.5
```

### 4. 启动服务

#### 方式一：一键启动（推荐）

```bash
chmod +x start_all.sh
./start_all.sh
```

#### 方式二：分别启动

```bash
# 终端1 - 启动后端
chmod +x start_backend.sh
./start_backend.sh

# 终端2 - 启动前端
chmod +x start_frontend.sh
./start_frontend.sh
```

#### 方式三：手动启动

```bash
# 启动后端
cd backend
python main.py

# 新开终端，启动前端
streamlit run frontend/app.py
```

### 5. 访问应用

- 🌐 **前端界面**: http://localhost:8501
- 📚 **后端API文档**: http://localhost:8000/docs

## 📖 使用指南

### 基本流程

1. **上传文档**
   - 在左侧面板点击"上传文档"
   - 选择PDF、TXT、MD或DOCX文件
   - 系统自动分块并向量化

2. **选择RAG技术**
   - 在左侧"RAG配置"中选择要对比的技术
   - 可选择多个技术同时运行
   - 调整检索参数（top_k、chunk_size等）

3. **配置评估**（可选）
   - 在左侧"自动评估配置"中
   - ☑️ 勾选"查询后自动评估"
   - ☑️ 勾选"使用Ragas评估"（更标准但更慢）

4. **提出问题**
   - 在中间对话窗口输入问题
   - 系统自动使用选定的RAG技术回答
   - 查看主答案和执行时间

5. **批量评估**
   - 在右侧"自动评估"窗口，点击「🚀 批量评估所有RAG技术」
   - 实时查看评估进度（1/8, 2/8, ...）
   - 等待评估完成（约1-2分钟）

6. **查看对比**
   - 在"统计对比"窗口查看详细表格
   - 分析可视化图表：LLM评分、Ragas评分、性能对比
   - 查看智能推荐的Top 3 RAG技术

7. **深入分析**
   - 切换标签页查看各RAG技术的详细答案
   - 查看检索到的文档片段和相似度
   - 查看LLM和Ragas的详细评分和反馈

### RAG技术说明

#### 🎯 已实现技术 (V1.2)

**基础检索增强** (3个)
- ✅ **Simple RAG**: 最基础的RAG实现
- ✅ **Reranker RAG**: 使用重排序模型优化检索结果
- ✅ **Fusion RAG**: 结合向量搜索和BM25关键词检索

**语义增强** (2个)
- ✅ **HyDE RAG**: 使用假设文档嵌入改善语义匹配
- ✅ **Contextual Compression**: 压缩和过滤检索上下文

**查询优化** (1个)
- ✨ **Query Transformation**: 查询重写、回退提示、子查询分解 **(NEW)**

**智能路由** (1个)
- ✨ **Adaptive RAG**: 根据查询类型自动选择最佳策略 **(NEW)**

**质量控制** (1个)
- ✨ **Self RAG**: 多重反思点确保答案质量 **(NEW)**

**总计: 8个RAG技术**

#### 🚧 后续扩展（规划中）
- **Corrective RAG (CRAG)**: 纠错RAG
- **Agentic RAG**: 智能体RAG
- **Graph RAG**: 基于知识图谱的检索
- **Hierarchical Indices**: 层次化索引
- **Context Enriched RAG**: 上下文增强
- ...更多技术持续添加中

#### 📚 详细文档
- 🚀 [批量评估快速上手](BATCH_EVAL_QUICKSTART.md) - 5分钟体验批量评估 **(NEW)**
- 🤖 [批量评估更新说明](BATCH_AUTO_EVAL_UPDATE.md) - V1.3批量评估功能完整指南 **(NEW)**
- 🤖 [自动评估指南](AUTO_EVALUATION_GUIDE.md) - 完整评估系统使用说明
- 📝 [自动评估总结](AUTO_EVALUATION_SUMMARY.md) - 实现细节和架构说明
- 💡 [新技术使用指南](NEW_TECHNIQUES_GUIDE.md) - 3个高级技术详解
- 📝 [V1.2更新日志](CHANGELOG_V1.2.md) - 完整变更记录
- 🚀 [快速启动V1.2](QUICKSTART_V1.2.md) - 5分钟上手新功能

## 🗂️ 项目结构

```
rag_all_app/
├── backend/                 # 后端服务
│   ├── api/                # API路由
│   │   ├── documents.py    # 文档管理API
│   │   ├── qa.py          # 问答API
│   │   └── evaluation.py  # 评分API
│   ├── core/              # 核心业务
│   │   ├── document_loader.py  # 文档加载器
│   │   └── vector_store.py     # 向量存储
│   ├── models/            # 数据模型
│   │   ├── db_models.py   # SQLAlchemy模型
│   │   └── schemas.py     # Pydantic模型
│   ├── utils/             # 工具函数
│   │   ├── embedding.py   # Embedding工具
│   │   ├── llm.py        # LLM调用
│   │   └── logger.py     # 日志配置
│   ├── config/            # 配置管理
│   │   └── settings.py   # 全局配置
│   └── main.py           # 主入口
├── frontend/              # 前端界面
│   ├── components/        # UI组件
│   │   ├── sidebar.py    # 左侧栏
│   │   ├── main_chat.py  # 对话窗口
│   │   └── rag_comparison.py  # 结果对比
│   └── app.py            # 主入口
├── rag_techniques/        # RAG技术实现
│   ├── base.py           # RAG基类
│   ├── simple_rag.py     # Simple RAG
│   └── ...              # 更多RAG技术
├── data/                 # 数据目录
│   ├── uploads/         # 上传文件
│   ├── vector_db/       # 向量数据库
│   └── rag_eval.db      # SQLite数据库
├── logs/                # 日志文件
├── requirements.txt     # 依赖列表
├── .env                # 环境配置
└── README.md           # 本文档
```

## 🔧 API文档

### 文档管理

```python
# 上传文档
POST /api/v1/documents/upload
Content-Type: multipart/form-data

# 获取文档列表
GET /api/v1/documents/

# 获取文档详情
GET /api/v1/documents/{document_id}

# 删除文档
DELETE /api/v1/documents/{document_id}
```

### 问答

```python
# 执行查询
POST /api/v1/qa/query
Content-Type: application/json
{
    "query": "什么是人工智能？",
    "document_ids": [1, 2],
    "rag_techniques": ["simple_rag"],
    "session_id": 1,
    "llm_config": {"temperature": 0.7},
    "rag_config": {"top_k": 5}
}

# 获取会话列表
GET /api/v1/qa/sessions

# 获取会话历史
GET /api/v1/qa/sessions/{session_id}/history
```

### 评分

```python
# 创建评分
POST /api/v1/evaluation/
Content-Type: application/json
{
    "qa_record_id": 1,
    "score_type": "human",
    "accuracy_score": 8.5,
    "relevance_score": 9.0,
    "fluency_score": 8.0,
    "completeness_score": 7.5,
    "overall_score": 8.25,
    "comments": "回答准确且完整"
}

# 获取对比统计
GET /api/v1/evaluation/stats/comparison
```

### 自动评估 (NEW!)

```python
# 单条自动评估
POST /api/v1/evaluation/auto
Content-Type: application/json
{
    "qa_record_id": 1,
    "use_llm_evaluator": true,
    "use_ragas": false,
    "reference_answer": null
}

# 批量自动评估
POST /api/v1/evaluation/auto/batch
Content-Type: application/json
{
    "qa_record_ids": [1, 2, 3, 4, 5],
    "use_llm_evaluator": true,
    "use_ragas": false
}
```

**评估维度**:
- **LLM评估**: 相关性、忠实度、连贯性、流畅度、简洁性
- **Ragas评估**: Faithfulness、Answer Relevancy、Context Precision/Recall
- **检索评估**: 检索精确度、上下文相关性

**详细文档**: 参考 [AUTO_EVALUATION_GUIDE.md](AUTO_EVALUATION_GUIDE.md)
```

## 🛠️ 开发指南

### 添加新的RAG技术

1. 在 `rag_techniques/` 下创建新文件
2. 继承 `BaseRAG` 类
3. 实现 `retrieve()` 和 `generate()` 方法
4. 在 `backend/api/qa.py` 中注册

示例：

```python
from rag_techniques.base import BaseRAG, RetrievedDoc

class CustomRAG(BaseRAG):
    def __init__(self, vector_store, config=None):
        super().__init__("Custom RAG", vector_store, config)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        # 实现检索逻辑
        pass
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        # 实现生成逻辑
        pass
```

### 数据库迁移

使用Alembic进行数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head
```

## 📊 性能优化建议

1. **向量维度**: 根据精度需求选择合适的embedding维度（512/768/1024）
2. **批量处理**: 大量文档上传时使用批量API
3. **缓存策略**: 对频繁查询的结果进行缓存
4. **异步处理**: 使用异步API提升并发性能

## 🐛 常见问题

### Q: 上传文档失败？
A: 检查文件格式是否支持，文件大小是否超过100MB限制

### Q: 向量检索没有结果？
A: 确认文档已成功向量化，检查embedding服务是否正常

### Q: LLM调用超时？
A: 调整timeout参数或检查LLM服务状态

### Q: 前端无法连接后端？
A: 确认后端服务已启动，检查端口是否被占用

## 📝 TODO List

**已完成** ✅:
- [x] LLM自动评分功能 (V1.3)
- [x] Ragas评估集成 (V1.3)
- [x] 8个RAG技术实现 (V1.2)
- [x] 多RAG技术对比
- [x] 实时问答系统

**进行中** 🔄:
- [ ] 前端自动评估可视化
- [ ] 添加更多RAG技术（目标20个）

**计划中** 📋:
- [ ] 支持多文档联合检索
- [ ] 导出评测报告（PDF/Excel）
- [ ] 用户认证系统
- [ ] Docker一键部署
- [ ] 多模态文档支持
- [ ] 异步批量评估
- [ ] 评估结果可视化看板

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 License

本项目采用MIT许可证

## 👥 作者

- 您的名字 - 初始工作

## 🙏 致谢

- 参考项目：rag-all-techniques-master
- FastAPI、Streamlit、LangChain等优秀开源项目

