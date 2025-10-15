# Ragas评估配置指南

## 概述

Ragas是一个专门用于RAG系统评估的框架，提供多维度的自动化评估指标。

## Ragas评估维度

### 三大关系评估

#### 1. 答案和上下文的关系
**faithfulness（忠实度）** - 0.0 到 1.0
- **评估内容**：答案是否基于检索到的上下文
- **评估方法**：LLM分析答案中的每个陈述是否能从上下文中找到依据
- **高分表示**：答案完全基于检索到的事实，没有幻觉
- **低分表示**：答案包含上下文中不存在的信息

#### 2. 答案和问题的关系
**answer_relevancy（答案相关性）** - 0.0 到 1.0
- **评估内容**：答案是否准确回答了问题
- **评估方法**：使用Embeddings计算答案和问题的语义相似度
- **高分表示**：答案直接、完整地回答了问题
- **低分表示**：答案偏离主题或不完整

#### 3. 问题和上下文的关系
**context_precision（上下文精确度）** - 0.0 到 1.0
- **评估内容**：相关上下文是否排在检索结果的前面
- **评估方法**：LLM评估每个上下文块与问题的相关性
- **高分表示**：最相关的上下文排在最前面
- **低分表示**：相关上下文被埋没在不相关内容中
- **⚠️ 注意**：需要ground_truth（标准答案）

**context_recall（上下文召回率）** - 0.0 到 1.0
- **评估内容**：是否检索到所有相关上下文
- **评估方法**：对比检索到的上下文和ground_truth
- **高分表示**：所有必要信息都被检索到
- **低分表示**：遗漏了重要信息
- **⚠️ 注意**：需要ground_truth（标准答案）

---

## 快速开始

### 1. 安装依赖

```bash
cd rag_all_app

# 方法1：使用安装脚本
chmod +x install_ragas_deps.sh
./install_ragas_deps.sh

# 方法2：手动安装
pip install langchain-openai==0.0.5
```

### 2. 配置环境变量（可选）

```bash
# 如果使用不同的API配置
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_API_KEY="your-api-key"
```

### 3. 重启服务

```bash
# 停止现有服务（Ctrl+C）

# 重启后端
cd backend
python main.py

# 新终端，重启前端
cd rag_all_app
streamlit run frontend/app.py
```

### 4. 使用Ragas评估

1. 在主页面选择RAG技术
2. 上传文档并提问
3. 在统计分析页面点击"批量评估"
4. 查看Ragas评分结果

---

## 配置说明

### 默认配置

```python
# backend/core/ragas_evaluator.py
RagasEvaluator(
    llm_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    llm_api_key="sk-e96412163b6a4f6189b65b98532eaf77",
    llm_model="qwen-plus",
    embedding_model="text-embedding-v3"
)
```

### 修改配置

如需使用不同的模型或API：

1. **修改环境变量**：
   ```bash
   export OPENAI_BASE_URL="your-api-url"
   export OPENAI_API_KEY="your-api-key"
   ```

2. **或修改代码**：
   编辑 `backend/core/ragas_evaluator.py`

---

## 数据存储结构

### 数据库Schema

Ragas评分存储在`evaluations`表的`metadata`字段：

```json
{
  "llm_evaluation": {
    "overall_score": 8.5,
    "relevance_score": 9.0,
    ...
  },
  "ragas_evaluation": {
    "ragas_available": true,
    "evaluation_success": true,
    ...
  },
  "ragas_scores": {
    "faithfulness": 0.85,
    "answer_relevancy": 0.90,
    "context_precision": 0.0,
    "context_recall": 0.0
  }
}
```

### 前端显示

对比表格包含以下列：
- **Ragas忠实度**：从`metadata.ragas_scores.faithfulness`读取
- **Ragas相关性**：从`metadata.ragas_scores.answer_relevancy`读取

格式化为3位小数显示（如：0.850）

---

## 常见问题

### Q1: Ragas评分全部为0？

**原因**：
- Ragas评估器未正确初始化
- 缺少langchain-openai依赖
- LLM或Embedding配置错误

**解决**：
```bash
# 1. 检查依赖
pip list | grep langchain-openai

# 2. 重新安装
pip install langchain-openai==0.0.5

# 3. 重启服务
```

### Q2: 评估时间过长？

**原因**：
- Ragas需要调用LLM进行评估
- faithfulness需要分析答案中的每个陈述

**解决**：
- 使用更快的LLM模型
- 减少并发评估数量
- 仅使用必要的指标

### Q3: context_precision和context_recall为0？

**原因**：
- 这两个指标需要ground_truth（标准答案）
- 当前实现没有提供标准答案

**说明**：
- 这是正常的
- 我们主要使用faithfulness和answer_relevancy
- 这两个指标不需要标准答案

### Q4: Ragas评分如何解读？

**评分范围**：0.0 - 1.0

**评分含义**：
- **0.9-1.0**: 优秀
- **0.7-0.9**: 良好
- **0.5-0.7**: 中等
- **< 0.5**: 需要改进

**示例**：
```
faithfulness: 0.85 → 85%的答案内容有上下文支持
answer_relevancy: 0.90 → 答案与问题相关度90%
```

---

## 技术架构

### 评估流程

```
1. 用户触发批量评估
   ↓
2. 前端调用 /api/v1/evaluations/auto
   ↓
3. 后端获取QA记录和检索上下文
   ↓
4. 创建RagasEvaluator实例
   ↓
5. 构建Dataset（question, answer, contexts）
   ↓
6. 调用ragas.evaluate()
   ├── LLM评估 faithfulness
   └── Embeddings计算 answer_relevancy
   ↓
7. 提取评分
   ↓
8. 保存到数据库metadata
   ↓
9. 返回结果到前端
   ↓
10. 前端显示在表格中
```

### 关键组件

#### 1. RagasEvaluator (backend/core/ragas_evaluator.py)
```python
class RagasEvaluator:
    def __init__(self, llm_model, embedding_model):
        self.llm = ChatOpenAI(...)
        self.embeddings = OpenAIEmbeddings(...)
    
    def evaluate_rag(self, question, answer, contexts):
        dataset = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [contexts]
        })
        
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy],
            llm=self.llm,
            embeddings=self.embeddings
        )
        
        return result
```

#### 2. 评估API (backend/api/evaluation.py)
```python
@router.post("/auto")
async def auto_evaluate(request: AutoEvaluationRequest):
    # LLM评估
    if request.use_llm_evaluator:
        llm_result = evaluator.evaluate_answer(...)
    
    # Ragas评估
    if request.use_ragas:
        ragas_result = ragas_evaluator.evaluate_rag(...)
    
    # 保存到数据库
    evaluation = DBEvaluation(
        ...
        meta_data={
            "ragas_scores": {
                "faithfulness": ...,
                "answer_relevancy": ...
            }
        }
    )
```

#### 3. 前端加载 (frontend/pages/statistics_page.py)
```python
def load_evaluations_from_db():
    # 从数据库读取评估记录
    evaluations = api.get(f"/evaluations/qa_record/{qa_record_id}")
    
    # 提取metadata中的Ragas评分
    metadata = evaluation.get("metadata", {})
    ragas_scores = metadata.get("ragas_scores", {})
    
    # 构造eval_result
    eval_result["ragas_evaluation"] = {
        "faithfulness": ragas_scores.get("faithfulness", 0),
        "answer_relevancy": ragas_scores.get("answer_relevancy", 0)
    }
```

---

## 性能优化

### 1. 并发控制

Ragas评估可能较慢，建议：
- 使用并发评估（已实现）
- 调整并发数量（UI可配置）

### 2. 指标选择

根据需求选择指标：
- **快速评估**：仅使用answer_relevancy（只需Embeddings）
- **全面评估**：使用faithfulness + answer_relevancy

### 3. 模型选择

- **快速模型**：qwen-turbo
- **平衡模型**：qwen-plus（默认）
- **高质量**：qwen-max

---

## 版本历史

- **V1.9.0** - 添加LLM和Embeddings配置支持
- **V1.9.1** - 完善数据库存储和前端加载
- **V1.9.2** - 添加详细日志和错误处理

---

## 相关文档

- [自动评估指南](AUTO_EVALUATION_GUIDE.md)
- [批量评估快速开始](BATCH_EVAL_QUICKSTART.md)
- [数据库迁移指南](MIGRATION_GUIDE.md)

---

## 支持

如遇到问题：
1. 查看日志：`backend/logs/app_*.log`
2. 检查依赖：`pip list | grep ragas`
3. 验证配置：`python3 -c "from langchain_openai import ChatOpenAI; print('OK')"`

