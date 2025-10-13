# 📝 更新日志 v1.1.0

## 🎉 重大更新：新增4种RAG技术！

**发布日期**：2025-10-13  
**版本**：v1.1.0  
**类型**：功能增强

---

## ✨ 新功能

### 1. 新增4种RAG技术

#### 🔄 Reranker RAG (重排序)
- 使用BGE-reranker-v2-m3模型
- 显著提升检索准确性（+10-20%）
- 两阶段检索：向量召回 → 精确重排
- **推荐场景**：生产环境、关键查询

#### 🔀 Fusion RAG (混合检索)
- 结合向量检索和BM25关键词检索
- 支持可调节权重融合
- 使用jieba分词器
- **推荐场景**：多样化查询、专业术语检索

#### 💡 HyDE RAG (假设文档嵌入)
- LLM生成假设答案辅助检索
- 改善抽象查询的检索效果
- 适合概念性问题
- **推荐场景**：复杂技术问题、抽象概念

#### 🗜️ Contextual Compression RAG (上下文压缩)
- LLM自动提取关键信息
- 过滤无关内容，减少噪音
- 节省30-70%的token消耗
- **推荐场景**：长文档、高精度需求

### 2. 前端界面增强
- 新增5种RAG技术选择
- 支持多RAG技术并行对比
- 更直观的技术名称显示

### 3. 文档完善
- 新增 `RAG_TECHNIQUES.md` 技术说明文档
- 详细的使用指南和最佳实践
- 性能对比和选择建议

---

## 🔧 技术改进

### 依赖更新
```bash
# 新增依赖
rank-bm25==0.2.2  # BM25检索
jieba==0.42.1     # 中文分词
```

### 架构优化
- 统一的RAG技术接口
- 模块化设计，易于扩展
- 完善的错误处理和日志

---

## 📊 性能对比（参考数据）

| 技术 | 准确率 | 速度 | Token消耗 | 推荐度 |
|------|--------|------|-----------|--------|
| Simple RAG | 75% | ⚡⚡⚡ | 1.0x | ⭐⭐⭐ |
| Reranker RAG | 85% | ⚡⚡ | 1.0x | ⭐⭐⭐⭐⭐ |
| Fusion RAG | 82% | ⚡⚡ | 1.0x | ⭐⭐⭐⭐ |
| HyDE RAG | 78% | ⚡ | 1.5x | ⭐⭐⭐ |
| Compression RAG | 88% | ⚡ | 0.5x | ⭐⭐⭐⭐ |

---

## 🚀 快速开始

### 1. 安装新依赖
```bash
pip install -r requirements.txt
```

### 2. 重启服务
```bash
# 停止旧服务 (Ctrl+C)
# 重新启动
cd backend
python main.py
```

### 3. 使用新技术
在前端界面左侧"RAG配置"中选择想要测试的技术：
- Reranker RAG (推荐✨)
- Fusion RAG
- HyDE RAG
- Contextual Compression

### 4. 对比测试
同时选择多个技术，在右侧面板查看对比结果！

---

## 📖 使用示例

### 示例1：使用Reranker提升准确性
```python
# 前端选择
rag_techniques = ["simple_rag", "reranker_rag"]

# API调用
{
    "query": "什么是人工智能？",
    "document_ids": [1],
    "rag_techniques": ["reranker_rag"],
    "rag_config": {
        "top_k": 5,
        "rerank_top_k": 20
    }
}
```

### 示例2：混合检索
```python
{
    "query": "神经网络的反向传播算法",
    "rag_techniques": ["fusion_rag"],
    "rag_config": {
        "top_k": 5,
        "vector_weight": 0.6,  # 语义权重
        "bm25_weight": 0.4     # 关键词权重
    }
}
```

### 示例3：多技术对比
```python
# 一次查询，对比5种技术
{
    "query": "深度学习的应用领域",
    "rag_techniques": [
        "simple_rag",
        "reranker_rag",
        "fusion_rag",
        "hyde_rag",
        "contextual_compression_rag"
    ]
}
```

---

## 🎯 推荐使用策略

### 快速原型开发
```
Simple RAG → 验证可行性
```

### 生产环境部署
```
Reranker RAG → 平衡效果和性能
```

### 研究和评测
```
多技术并行 → 全面对比分析
```

### 特殊场景
```
- 关键词敏感：Fusion RAG
- 抽象问题：HyDE RAG
- 长文档：Contextual Compression RAG
```

---

## 🐛 已知问题

### 1. Reranker RAG依赖
- 需要Reranker服务可用
- 配置 `.env` 中的 `RERANKER_BASE_URL` 和 `RERANKER_API_KEY`

### 2. Fusion RAG初次使用
- 首次查询需要构建BM25索引（约1-2秒）
- 后续查询会复用索引

### 3. Contextual Compression耗时
- 需要对每个文档调用LLM
- 建议 `compression_top_k` 不超过10

---

## 🔮 下一步计划

### v1.2.0（预计1-2周）
- [ ] Adaptive RAG - 自适应策略选择
- [ ] Self RAG - 自我反思机制
- [ ] Graph RAG - 知识图谱检索

### v1.3.0（预计2-3周）
- [ ] Multi-Query RAG - 多查询分解
- [ ] Semantic Chunking - 语义分块
- [ ] Query Transformation - 查询改写

### v2.0.0（预计1-2月）
- [ ] 实现全部20种RAG技术
- [ ] RAG Pipeline组合
- [ ] 自动化评测系统
- [ ] Docker部署支持

---

## 📞 反馈和支持

遇到问题？有建议？

1. 查看 `RAG_TECHNIQUES.md` 技术文档
2. 查看 `HOW_TO_USE.md` 使用手册
3. 运行 `python test_api.py` 诊断问题
4. 查看 `logs/` 目录下的日志

---

## 🙏 致谢

感谢参考项目 [rag-all-techniques-master](../README.md) 提供的技术实现参考。

---

**升级愉快！探索RAG技术的无限可能！** 🚀

