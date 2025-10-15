# RAG日志增强指南

## 概述

为每个RAG技术添加详细的执行日志，记录中间过程的所有关键步骤、数据和决策。

## 日志增强原则

### 1. 完整性
- 记录RAG流程的每个关键步骤
- 包含中间数据的统计信息
- 捕获异常和错误情况

### 2. 可读性
- 使用清晰的步骤名称（step name）
- 提供有意义的消息描述
- 结构化的详细信息（details）

### 3. 有用性
- 记录关键决策点和参数
- 包含数据预览（前N个元素）
- 记录性能相关的统计（长度、数量、分数等）

## 标准日志模式

### 基础模式

每个RAG技术应该包含以下标准日志点：

```python
# 1. 检索准备
self._log("retrieve_prepare", "准备开始检索", {
    "query_preview": query[:50] + "..." if len(query) > 50 else query,
    "query_length": len(query),
    "top_k": top_k
})

# 2. 检索完成
self._log("retrieve_complete", f"检索完成，找到 {len(results)} 个文档", {
    "result_count": len(results),
    "top_scores": [round(r.score, 4) for r in results[:3]]
})

# 3. 文档详情（前3个）
for idx, doc in enumerate(results[:3]):
    self._log(f"retrieve_doc_{idx+1}", f"文档 #{idx+1}", {
        "filename": doc.metadata.get("filename", "Unknown"),
        "score": round(doc.score, 4),
        "content_length": len(doc.content),
        "content_preview": doc.content[:100] + "..."
    })

# 4. 生成准备
self._log("generate_prepare_context", "准备上下文信息", {
    "doc_count": len(retrieved_docs),
    "total_context_length": sum(len(doc.content) for doc in retrieved_docs)
})

# 5. LLM调用
self._log("generate_llm_call", "调用LLM生成答案")

# 6. 生成完成
self._log("generate_complete", "答案生成成功", {
    "answer_length": len(answer),
    "answer_preview": answer[:150] + "..."
})

# 7. 错误处理
self._log("error_name", f"错误描述: {str(e)}", {"error": str(e)})
```

### 技术特定模式

根据不同RAG技术的特点，添加特定的日志点：

#### Fusion RAG（融合检索）
```python
# BM25索引构建
self._log("bm25_index_complete", "BM25索引构建完成", {
    "doc_count": len(self.bm25_corpus),
    "total_tokens": total_tokens,
    "avg_tokens_per_doc": avg_tokens
})

# 融合过程
self._log("fusion_merge", "结果合并完成", {
    "total_unique_docs": len(fusion_scores),
    "overlap_docs": overlap_count,
    "vector_only": vector_only_count,
    "bm25_only": bm25_only_count
})
```

#### HyDE RAG（假设文档生成）
```python
# 生成假设文档
self._log("hyde_generate_hypothetical", "生成假设文档", {
    "hypothetical_doc_length": len(hypothetical_doc),
    "hypothetical_preview": hypothetical_doc[:150]
})
```

#### Reranker RAG（重排序）
```python
# 重排序前
self._log("rerank_before", "重排序前", {
    "doc_count": len(docs),
    "original_top_scores": [round(d.score, 4) for d in docs[:3]]
})

# 重排序后
self._log("rerank_after", "重排序完成", {
    "reranked_count": len(reranked_docs),
    "new_top_scores": [round(d.score, 4) for d in reranked_docs[:3]]
})
```

#### Query Transformation RAG（查询转换）
```python
# 查询重写
self._log("query_rewrite", "查询重写完成", {
    "original_query": original_query,
    "rewritten_query": rewritten_query
})

# 多查询分解
self._log("query_decompose", "查询分解完成", {
    "original_query": query,
    "sub_queries": sub_queries,
    "sub_query_count": len(sub_queries)
})
```

#### Self RAG（自我反思）
```python
# 相关性检查
self._log("self_rag_relevance_check", "检查文档相关性", {
    "relevant_count": relevant_count,
    "total_count": total_count,
    "relevance_rate": round(relevant_count / total_count, 3)
})

# 答案评估
self._log("self_rag_answer_eval", "答案质量评估", {
    "is_supported": is_supported,
    "is_useful": is_useful,
    "final_decision": "采用" if use_answer else "重新生成"
})
```

#### Adaptive RAG（自适应）
```python
# 策略选择
self._log("adaptive_strategy_select", f"选择策略: {selected_strategy}", {
    "query_type": query_type,
    "strategy": selected_strategy,
    "reason": selection_reason
})
```

#### CRAG（矫正检索）
```python
# 相关性评估
self._log("crag_relevance_eval", "文档相关性评估", {
    "high_relevance_count": high_count,
    "medium_relevance_count": medium_count,
    "low_relevance_count": low_count,
    "action": action  # "使用高相关文档" / "补充检索" / "网络搜索"
})
```

## 日志查看

前端会在"执行日志"标签页展示这些日志，格式为：

```
总耗时: 2.35s  检索: 0.45s, 生成: 1.90s

[2025-10-15 15:00:00] [init] 开始执行 Fusion RAG
  - query: "多智能体的应用..."
  - query_length: 15
  
[2025-10-15 15:00:00] [vector_search_start] 开始向量检索，top_k=10
  
[2025-10-15 15:00:00] [vector_search_complete] 向量检索完成
  - result_count: 10
  - top_scores: [0.9234, 0.8876, 0.8654]
  
[2025-10-15 15:00:01] [bm25_index_complete] BM25索引构建完成
  - doc_count: 10
  - total_tokens: 3542
  
...
```

## 实施建议

### 优先级

1. **高优先级**（已完成）：
   - Simple RAG ✅
   - Fusion RAG ✅

2. **中优先级**（建议接下来完善）：
   - HyDE RAG
   - Reranker RAG
   - Query Transformation RAG
   - Self RAG
   - Adaptive RAG
   - CRAG

3. **基础日志**（快速添加）：
   - 其他所有RAG技术

### 快速添加基础日志

对于复杂度较低的RAG技术，至少添加以下基础日志：

```python
# retrieve方法
self._log("retrieve_prepare", "开始检索", {"query_length": len(query), "top_k": top_k})
self._log("retrieve_complete", f"检索完成，找到 {len(results)} 个文档", {
    "result_count": len(results)
})

# generate方法
self._log("generate_prepare_context", "准备上下文", {"doc_count": len(retrieved_docs)})
self._log("generate_llm_call", "调用LLM生成答案")
self._log("generate_complete", "生成完成", {"answer_length": len(answer)})
```

## 注意事项

1. **性能影响**：日志记录本身应该尽量轻量，避免大量字符串操作
2. **敏感信息**：不要在日志中记录完整的用户数据或敏感信息
3. **预览长度**：大文本只记录前N个字符的预览
4. **列表截断**：长列表只记录前几个元素
5. **错误捕获**：所有日志调用应该在try-except块外部或内部，但不影响主流程

## 测试验证

完成日志增强后，应该：

1. 在前端执行RAG查询
2. 切换到"执行日志"标签页
3. 验证日志是否：
   - ✅ 完整记录了关键步骤
   - ✅ 包含有用的中间数据
   - ✅ 易于理解和调试
   - ✅ 格式清晰美观

## 版本历史

- V1.9.4 (2025-10-15): 创建日志增强指南
- V1.9.4 (2025-10-15): 完成 Simple RAG 和 Fusion RAG 日志增强

---

通过这个指南，我们确保每个RAG技术都有详细、标准化的日志记录，方便用户理解和调试RAG流程。

