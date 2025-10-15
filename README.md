# 🤖 RAG评测对比平台 V1.9

一个支持20+种RAG技术的评测与对比系统，集成LLM和Ragas双重自动评估，让您能够直观地比较不同RAG方案的效果。

## 🌟 最新特性

### V1.9 - Ragas完整集成与数据优化 (NEW! 2025-10-15)
- 🎯 **Ragas完整配置**: LLM + Embeddings双模型支持，4维度标准化评估
- 💾 **完整数据存储**: 所有评分维度完整保存（LLM 6维度 + Ragas 4维度）
- 📊 **评分可视化**: 对比表格显示10列完整评分数据
- 🔄 **数据库迁移**: 智能迁移工具，保留原有数据
- 📈 **自动加载**: 从数据库自动加载历史评估数据
- 🎨 **前端优化**: 三页面重新设计，主页面、对比页面、统计页面全面优化
- 🚀 **并发优化**: RAG查询和评估支持可配置并发，大幅提升性能
- 📝 **详细日志**: 每个RAG技术记录完整执行过程

### V1.8 - RAG技术大扩展 (2025-10-14)
- ✨ **20种RAG技术**: 从基础到高级，全面覆盖主流RAG方案
- 🔧 **纠错与增强**: CRAG、Context Enriched、Contextual Chunk Headers
- 📚 **优化策略**: Hierarchical Indices、Document Augmentation、Semantic Chunking
- 🎯 **精细化策略**: RSE、Chunk Size Selector、Proposition Chunking、Graph RAG
- ⚡ **性能优化**: 并发查询、并发评估，可自定义并发数量

### V1.3 - 批量自动评估与统计对比 (2025-10-13)
- 🤖 **LLM自动评分**: 6维度智能评分（相关性、忠实度、连贯性、流畅度、简洁性、综合）
- 📊 **Ragas集成**: 标准化RAG评估指标（Faithfulness、Answer Relevancy等）
- ⚡ **批量评估**: 一键评估所有选中的RAG技术，实时进度显示
- 📈 **统计对比**: 详细对比表格 + 可视化图表 + 智能推荐
- 💾 **自动保存**: 评估结果自动持久化到数据库
- 🎯 **检索质量评估**: 自动评估检索精确度和上下文相关性

## 📋 核心特性

### 评估系统
- ✅ **双重自动评估**: LLM评分 + Ragas评分，全面评估RAG质量
- ✅ **多维度评分**: 10个评分维度，涵盖答案质量的各个方面
  - **LLM评分**: 相关性、忠实度、连贯性、流畅性、简洁性、综合得分
  - **Ragas评分**: Faithfulness、Answer Relevancy、Context Precision/Recall
- ✅ **批量评估**: 一键评估所有RAG技术，支持并发加速
- ✅ **历史追溯**: 所有评估结果持久化存储，支持历史查询

### RAG技术
- ✅ **20+种技术**: 覆盖基础到高级的主流RAG技术
- ✅ **技术对比**: 同时运行多个RAG技术，并列展示结果
- ✅ **详细溯源**: 展示检索文档、相似度分数、执行日志
- ✅ **并发优化**: 可配置并发数量，大幅提升查询和评估速度

### 文档管理
- ✅ **多格式支持**: PDF、TXT、MD、DOCX等
- ✅ **智能分块**: 自动分块并向量化
- ✅ **向量存储**: Milvus Lite向量数据库

### 可视化分析
- ✅ **对比表格**: 完整展示10列评分数据
- ✅ **可视化图表**: 折线图、散点图多维度展示
- ✅ **智能推荐**: 基于评分自动推荐Top 3 RAG技术
- ✅ **AI分析报告**: LLM生成的深度分析报告

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     RAG评测对比平台 V1.9                          │
├─────────────────────────────────────────────────────────────────┤
│  前端 (Streamlit) - 三页面设计                                    │
│  ┌────────────┬──────────────┬─────────────────────────┐        │
│  │ 主页面     │  RAG对比页面 │  统计分析页面           │        │
│  │ ·配置区    │  ·历史消息   │  ·对比表格             │        │
│  │ ·对话区    │  ·RAG标签   │  ·可视化图表           │        │
│  │ ·知识库    │  ·答案展示   │  ·智能推荐             │        │
│  │            │  ·文档日志   │  ·AI分析报告           │        │
│  └────────────┴──────────────┴─────────────────────────┘        │
├─────────────────────────────────────────────────────────────────┤
│  后端 (FastAPI)                                                  │
│  ┌────────────────────────────────────────────────────┐         │
│  │  API层: Documents | QA | Evaluation                │         │
│  ├────────────────────────────────────────────────────┤         │
│  │  业务层: DocumentLoader | VectorStore | RAGChain   │         │
│  ├────────────────────────────────────────────────────┤         │
│  │  评估层: AutoEvaluator | RagasEvaluator            │         │
│  ├────────────────────────────────────────────────────┤         │
│  │  RAG技术: 20+种技术实现                            │         │
│  │  · 基础检索增强 (5)  · 高级技术 (5)               │         │
│  │  · 纠错与增强 (3)    · 优化策略 (3)               │         │
│  │  · 精细化策略 (4)                                  │         │
│  └────────────────────────────────────────────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  数据层                                                          │
│  ┌──────────────┬──────────────────────────────────────┐       │
│  │ SQLite       │ Milvus Lite (向量数据库)              │       │
│  │ (元数据)     │ (文档向量)                            │       │
│  │ · Documents  │ · 分块文档                            │       │
│  │ · Sessions   │ · Embedding向量                       │       │
│  │ · QARecords  │ · 相似度检索                          │       │
│  │ · Evaluations│                                       │       │
│  └──────────────┴──────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- 10GB+ 磁盘空间
- 可访问的LLM和Embedding API（阿里云百炼等）

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/your-repo/rag_eval_project.git
cd rag_eval_project/rag_all_app

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装Ragas评估依赖
chmod +x install_ragas_deps.sh
./install_ragas_deps.sh
```

### 3. 配置环境变量（可选）

编辑配置或设置环境变量：

```bash
# LLM和Embedding配置（默认使用阿里云百炼）
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_API_KEY="your-api-key"
```

### 4. 数据库迁移（首次使用或升级后）

```bash
# 执行数据库迁移
python3 migrate_database.py
```

### 5. 启动服务

#### 方式一：一键启动（推荐）

```bash
chmod +x start_all.sh
./start_all.sh
```

#### 方式二：分别启动

```bash
# 终端1 - 启动后端
cd backend
python main.py

# 终端2 - 启动前端
streamlit run frontend/app.py
```

### 6. 访问应用

- 🌐 **前端界面**: http://localhost:8501
- 📚 **后端API文档**: http://localhost:8000/docs

## 📖 使用指南

### 快速上手（5分钟）

1. **上传文档**
   - 主页面右侧"知识库"区域
   - 点击"上传文档"，选择PDF/TXT/MD/DOCX文件
   - 可选中多个文档并点击"☑️ 全选"

2. **选择RAG技术**
   - 主页面配置区，勾选想要对比的RAG技术
   - 建议选择3-5个进行对比
   - 可调整RAG查询并发数（加速查询）

3. **提出问题**
   - 在对话区输入问题
   - 系统并发执行所有选中的RAG技术
   - 主对话窗口显示第一个技术的答案

4. **切换到"RAG对比"页面**
   - 查看不同RAG技术的答案对比
   - 点击RAG标签切换查看
   - 右侧查看检索文档（分页显示）和执行日志

5. **切换到"统计分析"页面**
   - 点击"🚀 批量评估所有RAG技术"
   - 等待自动评估完成（1-2分钟）
   - 查看完整的对比表格（10列评分数据）
   - 分析可视化图表
   - 查看Top 3推荐和AI分析报告

### RAG技术说明

#### 🎯 已实现技术 (20种)

**基础检索增强** (5个)
- ✅ **Simple RAG**: 最基础的RAG实现
- ✅ **Reranker RAG**: 使用LLM重排序优化检索结果
- ✅ **Fusion RAG**: 结合向量搜索和BM25关键词检索
- ✅ **HyDE RAG**: 使用假设文档嵌入改善语义匹配
- ✅ **Contextual Compression RAG**: 压缩和过滤检索上下文

**高级技术** (5个)
- ✅ **Query Transformation RAG**: 查询重写、回退提示、子查询分解
- ✅ **Adaptive RAG**: 根据查询类型自动选择最佳策略
- ✅ **Self RAG**: 多重反思点确保答案质量
- ✅ **CRAG**: 纠错RAG，动态调整检索策略
- ✅ **Graph RAG**: 基于知识图谱的检索增强

**纠错与增强** (2个)
- ✅ **Context Enriched RAG**: 上下文增强，扩展检索范围
- ✅ **Contextual Chunk Headers RAG**: 为文档块添加描述性标题

**优化策略** (3个)
- ✅ **Hierarchical Indices RAG**: 两层索引系统，先检索摘要再检索详情
- ✅ **Document Augmentation RAG**: 为每个文档块生成问题增强检索
- ✅ **Semantic Chunking RAG**: 基于语义边界的动态分块

**精细化策略** (4个)
- ✅ **RSE RAG**: 句子级检索，更细粒度的信息提取
- ✅ **Chunk Size Selector RAG**: 动态选择最优分块大小
- ✅ **Proposition Chunking RAG**: 原子命题级分块和检索
- ✅ **Feedback Loop RAG**: 基于反馈持续优化检索策略（规划中）

**总计: 20种RAG技术**

### 评估系统详解

#### LLM自动评分（6个维度）

1. **相关性 (relevance_score)**: 答案与问题的相关程度
2. **忠实度 (faithfulness_score)**: 答案是否基于检索内容
3. **连贯性 (coherence_score)**: 答案逻辑是否连贯
4. **流畅性 (fluency_score)**: 答案语言是否流畅
5. **简洁性 (conciseness_score)**: 答案是否简洁
6. **综合得分 (overall_score)**: 以上维度的加权平均

#### Ragas标准化评分（4个维度）

1. **faithfulness**: 答案-上下文关系，答案是否基于上下文
2. **answer_relevancy**: 答案-问题关系，答案是否回答问题
3. **context_precision**: 问题-上下文关系，相关上下文排序
4. **context_recall**: 问题-上下文关系，是否检索全部相关信息

**注**: context_precision和context_recall需要标准答案（ground_truth）

#### 评分解读

- **0.9-1.0** (9-10分): 优秀
- **0.7-0.9** (7-9分): 良好
- **0.5-0.7** (5-7分): 中等
- **< 0.5** (< 5分): 需要改进

## 🔧 高级配置

### 并发控制

```python
# 主页面配置区
RAG查询并发数: 3  # 同时执行3个RAG技术
评估并发数: 3     # 同时评估3个结果
```

### Ragas配置

```python
# backend/core/ragas_evaluator.py
RagasEvaluator(
    llm_model="qwen-plus",           # LLM模型
    embedding_model="text-embedding-v3",  # Embedding模型
    llm_base_url="...",              # API地址
    llm_api_key="..."                # API密钥
)
```

### 数据库配置

```python
# backend/models/database.py
DATABASE_URL = "sqlite:///./data/rag_eval.db"
```

## 📚 详细文档

### 快速指南
- 🚀 [5分钟快速开始](QUICKSTART_V1.2.md)
- 🚀 [批量评估快速上手](BATCH_EVAL_QUICKSTART.md)
- 📖 [Ragas配置指南](RAGAS_SETUP_GUIDE.md) **(NEW)**
- 🔄 [数据库迁移指南](MIGRATION_GUIDE.md) **(NEW)**

### 功能文档
- 🤖 [自动评估完整指南](AUTO_EVALUATION_GUIDE.md)
- 📊 [批量评估功能说明](BATCH_AUTO_EVAL_UPDATE.md)
- 💡 [RAG技术详解](RAG_TECHNIQUES.md)
- 📝 [新技术使用指南](NEW_TECHNIQUES_GUIDE.md)

### 技术文档
- 🏗️ [系统架构](architecture.md)
- 📦 [API文档](api.md)
- 🗂️ [数据模型](data_model.md)
- 🔧 [开发指南](best_practices.md)

### 更新日志
- 📝 [V1.3更新日志](CHANGELOG_V1.3.md)
- 📝 [V1.2更新日志](CHANGELOG_V1.2.md)
- 🎉 [V1.3发布说明](VERSION_1.3_RELEASE_NOTES.md)

## 🗂️ 项目结构

```
rag_all_app/
├── backend/                     # 后端服务
│   ├── api/                    # API路由
│   │   ├── documents.py        # 文档管理API
│   │   ├── qa.py              # 问答API（并发支持）
│   │   └── evaluation.py      # 评估API（LLM + Ragas）
│   ├── core/                  # 核心业务
│   │   ├── document_loader.py  # 文档加载器
│   │   ├── vector_store.py     # 向量存储
│   │   ├── auto_evaluator.py   # LLM自动评估器
│   │   └── ragas_evaluator.py  # Ragas评估器
│   ├── models/                # 数据模型
│   │   ├── db_models.py       # SQLAlchemy模型
│   │   ├── schemas.py         # Pydantic模型
│   │   └── database.py        # 数据库连接
│   ├── migrations/            # 数据库迁移
│   │   └── migrate_v1_8_7.py  # V1.8.7迁移脚本
│   ├── utils/                 # 工具函数
│   │   ├── embedding.py       # Embedding工具
│   │   ├── llm.py            # LLM调用
│   │   └── logger.py         # 日志配置
│   └── main.py               # 后端入口
├── frontend/                  # 前端界面
│   ├── pages/                # 页面模块
│   │   ├── main_page.py      # 主页面
│   │   ├── comparison_page.py # RAG对比页面
│   │   └── statistics_page.py # 统计分析页面
│   ├── components/           # UI组件（已废弃）
│   └── app.py               # 前端入口
├── rag_techniques/           # RAG技术实现（20种）
│   ├── base.py              # RAG基类
│   ├── simple_rag.py        # Simple RAG
│   ├── reranker_rag.py      # Reranker RAG
│   ├── fusion_rag.py        # Fusion RAG
│   ├── hyde_rag.py          # HyDE RAG
│   ├── contextual_compression_rag.py
│   ├── query_transformation_rag.py
│   ├── adaptive_rag.py
│   ├── self_rag.py
│   ├── crag.py
│   ├── context_enriched_rag.py
│   ├── contextual_chunk_headers_rag.py
│   ├── hierarchical_rag.py
│   ├── doc_augmentation_rag.py
│   ├── semantic_chunking_rag.py
│   ├── rse_rag.py
│   ├── chunk_size_selector_rag.py
│   ├── proposition_chunking_rag.py
│   └── graph_rag.py
├── data/                    # 数据目录
│   ├── uploads/            # 上传文件
│   └── vector_db/          # 向量数据库
├── docs/                   # 文档目录
├── requirements.txt        # Python依赖
├── migrate_database.py     # 数据库迁移脚本
├── install_ragas_deps.sh   # Ragas依赖安装脚本
└── README.md              # 本文档
```

## 🔧 API文档

### 核心API

#### 文档管理
```http
POST   /api/v1/documents/upload      # 上传文档
GET    /api/v1/documents/             # 获取文档列表
GET    /api/v1/documents/{id}         # 获取文档详情
DELETE /api/v1/documents/{id}         # 删除文档
```

#### 问答
```http
POST   /api/v1/qa/query              # 执行查询（并发支持）
GET    /api/v1/qa/sessions            # 获取会话列表
GET    /api/v1/qa/sessions/{id}/history  # 获取会话历史
```

#### 评估
```http
POST   /api/v1/evaluations/          # 创建评分
POST   /api/v1/evaluations/auto      # 单条自动评估
POST   /api/v1/evaluations/auto/batch # 批量自动评估
GET    /api/v1/evaluations/qa_record/{id}  # 获取QA记录的评估
GET    /api/v1/evaluations/stats/comparison # 获取对比统计
```

详细API文档请访问: http://localhost:8000/docs

## 🛠️ 开发指南

### 添加新的RAG技术

1. 创建新文件 `rag_techniques/your_rag.py`
2. 继承 `BaseRAG` 类
3. 实现 `retrieve()` 和 `generate()` 方法
4. 在 `backend/api/qa.py` 中注册

示例：
```python
from rag_techniques.base import BaseRAG, RetrievedDoc
from typing import List

class YourRAG(BaseRAG):
    def __init__(self, vector_store, config=None):
        super().__init__("Your RAG", vector_store, config)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        self._log("retrieve_start", "开始检索")
        # 实现检索逻辑
        results = self.vector_store.similarity_search(query, k=top_k)
        retrieved_docs = [
            RetrievedDoc(
                chunk_id=r.chunk_id,
                content=r.content,
                score=r.score,
                metadata=r.metadata
            )
            for r in results
        ]
        self._log("retrieve_end", f"检索到{len(retrieved_docs)}个文档")
        return retrieved_docs
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        self._log("generate_start", "开始生成答案")
        # 实现生成逻辑
        context = "\n\n".join([doc.content for doc in retrieved_docs])
        answer = self._generate_with_llm(query, context)
        self._log("generate_end", "答案生成完成")
        return answer
```

### 数据库迁移

```bash
# 执行迁移
python3 migrate_database.py

# 或使用Alembic（高级）
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### 运行测试

```bash
# 测试API
python test_api.py

# 测试自动评估
python test_auto_evaluation.py

# 测试批量评估
python test_batch_evaluation_flow.py
```

## 📊 性能优化

1. **并发控制**: 调整RAG查询和评估的并发数量
2. **缓存策略**: 对频繁查询启用缓存
3. **批量处理**: 使用批量API提升效率
4. **向量维度**: 根据需求选择embedding维度
5. **模型选择**: 根据速度和质量需求选择合适的LLM

## 🐛 常见问题

### Q1: Ragas评分全部为0？
**A**: 
1. 检查是否安装了`langchain-openai`: `pip install langchain-openai==0.0.5`
2. 重启后端服务
3. 查看日志: `backend/logs/app_*.log`

### Q2: 评估超时？
**A**: 
1. 减少并发评估数量
2. 仅使用LLM评估，不使用Ragas
3. 检查API服务是否正常

### Q3: 数据库迁移失败？
**A**: 
1. 备份数据库: `cp backend/data/rag_eval.db backend/data/rag_eval.db.backup`
2. 停止所有服务
3. 重新执行迁移: `python3 migrate_database.py`

### Q4: 前端表格不显示评分？
**A**: 
1. 确认已执行批量评估
2. 刷新页面（Ctrl+Shift+R）
3. 检查是否从数据库加载了历史数据

### Q5: 上传文档失败？
**A**: 
1. 检查文件格式（支持PDF、TXT、MD、DOCX）
2. 检查文件大小（建议<100MB）
3. 查看后端日志确认错误信息

## 📝 更新计划

**已完成** ✅:
- [x] 20种RAG技术实现
- [x] LLM自动评分（6维度）
- [x] Ragas评估集成（4维度）
- [x] 批量自动评估
- [x] 并发优化（查询+评估）
- [x] 完整数据存储
- [x] 数据库迁移工具
- [x] 前端三页面重新设计
- [x] 详细执行日志

**进行中** 🔄:
- [ ] Feedback Loop RAG实现
- [ ] 更多可视化图表
- [ ] 导出评测报告（PDF/Excel）

**计划中** 📋:
- [ ] 多文档联合检索
- [ ] 用户认证系统
- [ ] Docker一键部署
- [ ] 多模态文档支持
- [ ] 实时协作功能

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 License

本项目采用MIT许可证

## 👥 致谢

- 参考项目：[rag-all-techniques-master](https://github.com/NirDiamant/RAG_Techniques)
- 感谢 FastAPI、Streamlit、LangChain、Ragas 等优秀开源项目
- 感谢阿里云百炼提供的LLM和Embedding服务

---

**Star ⭐ 本项目，持续关注更新！**

如有问题，欢迎提Issue或查看[文档目录](docs/)
