# 🎯 RAG技术说明文档

本文档详细介绍平台支持的5种RAG技术及其特点。

## 📚 技术列表

| 技术 | 难度 | 效果 | 速度 | 适用场景 |
|------|------|------|------|----------|
| Simple RAG | ⭐ | ⭐⭐⭐ | ⚡⚡⚡ | 基础问答、快速原型 |
| Reranker RAG | ⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | 高精度检索、关键查询 |
| Fusion RAG | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡⚡ | 混合查询、多样化检索 |
| HyDE RAG | ⭐⭐ | ⭐⭐⭐ | ⚡ | 抽象查询、概念检索 |
| Contextual Compression | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⚡ | 长文档、噪音过滤 |

---

## 1️⃣ Simple RAG (基础RAG)

### 原理
最基础的RAG实现，使用向量相似度直接检索文档。

### 流程
```
用户查询 → 向量化 → 向量检索 → 文档召回 → LLM生成答案
```

### 优点
- ✅ 实现简单
- ✅ 速度快
- ✅ 资源占用少
- ✅ 易于理解和调试

### 缺点
- ❌ 可能检索到不相关文档
- ❌ 依赖embedding质量
- ❌ 无法处理关键词匹配

### 适用场景
- 基础文档问答
- 快速原型验证
- 资源受限环境

### 参数配置
```python
{
    "top_k": 5,           # 检索文档数量
    "chunk_size": 500,    # 分块大小
    "chunk_overlap": 100  # 重叠大小
}
```

---

## 2️⃣ Reranker RAG (重排序RAG)

### 原理
先用向量检索获取候选文档，再用专门的重排序模型精确打分，选出最相关的文档。

### 流程
```
用户查询 → 向量检索(top 20) → Reranker重排序 → 选择top 5 → LLM生成
```

### 优点
- ✅ 显著提升检索准确性
- ✅ 过滤不相关文档
- ✅ 适用于关键任务
- ✅ 效果提升明显（通常+10-20%）

### 缺点
- ❌ 增加一次模型调用
- ❌ 延迟略高
- ❌ 需要Reranker服务

### 适用场景
- 对准确性要求高的场景
- 关键业务查询
- 复杂文档集合

### 参数配置
```python
{
    "top_k": 5,           # 最终返回数量
    "rerank_top_k": 20,   # 候选文档数量
}
```

### 使用建议
- 候选文档数建议为最终数量的3-4倍
- Reranker模型推荐：bge-reranker-v2-m3
- 适合处理10-50个候选文档

---

## 3️⃣ Fusion RAG (融合RAG)

### 原理
同时使用向量检索（语义匹配）和BM25（关键词匹配），融合两种检索结果。

### 流程
```
              ┌→ 向量检索 → 得分归一化 ┐
用户查询 → 分词 ┤                      ├→ 加权融合 → LLM生成
              └→ BM25检索 → 得分归一化 ┘
```

### 优点
- ✅ 结合语义和关键词优势
- ✅ 对不同类型查询鲁棒
- ✅ 提高召回率
- ✅ 适应性强

### 缺点
- ❌ 需要构建BM25索引
- ❌ 计算量较大
- ❌ 需要调整权重参数

### 适用场景
- 多样化查询类型
- 需要精确关键词匹配
- 既有概念查询又有专业术语

### 参数配置
```python
{
    "top_k": 5,
    "vector_weight": 0.5,  # 向量检索权重
    "bm25_weight": 0.5,    # BM25检索权重
}
```

### 权重调整建议
- 概念性查询：`vector_weight=0.7, bm25_weight=0.3`
- 关键词查询：`vector_weight=0.3, bm25_weight=0.7`
- 均衡模式：`vector_weight=0.5, bm25_weight=0.5`

---

## 4️⃣ HyDE RAG (假设文档嵌入)

### 原理
不直接用用户查询检索，而是先让LLM生成一个"假设的答案"，用这个假设答案去检索。

### 流程
```
用户查询 → LLM生成假设答案 → 用假设答案检索 → 获取真实文档 → LLM生成最终答案
```

### 优点
- ✅ 改善查询-文档语义匹配
- ✅ 处理抽象或复杂查询
- ✅ 提高检索召回率
- ✅ 适合概念性问题

### 缺点
- ❌ 需要额外LLM调用
- ❌ 延迟较高
- ❌ token消耗增加
- ❌ 可能产生误导性假设

### 适用场景
- 抽象概念查询
- 复杂技术问题
- 需要深度理解的查询

### 参数配置
```python
{
    "top_k": 5,
    "num_hypotheses": 1,  # 生成假设文档数量
}
```

### 使用建议
- 适合处理"为什么"、"怎么样"类问题
- 不适合简单的事实查询
- 假设文档长度建议300-500字符

---

## 5️⃣ Contextual Compression RAG (上下文压缩)

### 原理
检索到文档后，用LLM提取每个文档中与查询最相关的关键信息，去除无关内容。

### 流程
```
用户查询 → 向量检索(top 10) → LLM逐个压缩文档 → 保留关键信息 → LLM生成答案
```

### 优点
- ✅ 去除无关信息和噪音
- ✅ 降低LLM输入token数
- ✅ 提高答案准确性
- ✅ 突出关键内容

### 缺点
- ❌ 需要多次LLM调用（每个文档一次）
- ❌ 延迟最高
- ❌ 成本较高
- ❌ 可能丢失部分上下文

### 适用场景
- 长文档处理
- 噪音较多的文档
- 对精确度要求极高的场景

### 参数配置
```python
{
    "top_k": 5,             # 最终返回数量
    "compression_top_k": 10 # 候选文档数量
}
```

### 使用建议
- 适合文档长度>1000字符的场景
- 压缩可节省30-70%的token
- 建议候选文档数为最终数量的2倍

---

## 🔄 技术对比

### 准确性排序
```
Contextual Compression ≈ Reranker > Fusion > HyDE > Simple
```

### 速度排序
```
Simple > Fusion > Reranker > HyDE > Contextual Compression
```

### 成本排序（LLM调用次数）
```
Simple(1次) < Reranker(1次) < Fusion(1次) < HyDE(2次) < Compression(n+1次)
```

### 实现复杂度
```
Simple < HyDE < Reranker < Fusion < Contextual Compression
```

---

## 💡 选择建议

### 场景1：快速原型
**推荐**：Simple RAG
- 快速验证可行性
- 了解数据质量

### 场景2：生产环境
**推荐**：Reranker RAG
- 平衡效果和性能
- 显著提升准确性

### 场景3：多样化查询
**推荐**：Fusion RAG
- 适应不同查询类型
- 提高鲁棒性

### 场景4：复杂问题
**推荐**：HyDE RAG + Reranker RAG 组合
- HyDE改善检索
- Reranker精确筛选

### 场景5：长文档高精度
**推荐**：Contextual Compression RAG
- 处理长文档
- 追求极致准确性

---

## 🎯 最佳实践

### 1. 单技术使用
```python
# 开发阶段：使用Simple RAG快速迭代
techniques = ["simple_rag"]

# 生产环境：使用Reranker RAG提升质量
techniques = ["reranker_rag"]
```

### 2. 多技术对比
```python
# 评测模式：同时测试多个技术
techniques = [
    "simple_rag",
    "reranker_rag", 
    "fusion_rag"
]
```

### 3. 技术组合（未来支持）
```python
# Pipeline组合
pipeline = [
    "fusion_rag",      # 混合检索
    "reranker_rag",    # 精确重排
    "compression_rag"  # 压缩优化
]
```

---

## 📊 性能参考

基于AI_Information.pdf测试（26个文本块）：

| 技术 | 平均耗时 | 准确率 | 相关性 | Token消耗 |
|------|---------|--------|--------|----------|
| Simple | 3.2s | 75% | 80% | 1000 |
| Reranker | 4.5s | 85% | 90% | 1000 |
| Fusion | 4.0s | 82% | 88% | 1000 |
| HyDE | 5.8s | 78% | 85% | 1500 |
| Compression | 8.5s | 88% | 92% | 600 |

*注：数据仅供参考，实际效果取决于文档质量和查询类型*

---

## 🔧 故障排除

### Reranker RAG失败
- 检查Reranker服务是否可用
- 验证API密钥正确
- 确认模型名称正确

### Fusion RAG慢
- 减少候选文档数量
- 调整检索参数
- 考虑使用Simple或Reranker

### HyDE生成不佳
- 调整温度参数（推荐0.7）
- 优化假设文档提示词
- 检查LLM服务质量

### Compression超时
- 减少compression_top_k
- 增加超时时间
- 使用更快的LLM

---

## 📚 参考资料

- [Simple RAG](../src/full/01_simple_rag.ipynb)
- [Reranker RAG](../src/full/08_reranker.ipynb)
- [Fusion RAG](../src/full/16_fusion_rag.ipynb)
- [HyDE RAG](../src/full/19_HyDE_rag.ipynb)
- [Contextual Compression](../src/full/10_contextual_compression.ipynb)

---

**下一步**：探索更多RAG技术？查看 [完整RAG技术列表](../README.md)

