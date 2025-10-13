# RAG评估平台 V1.2 快速启动指南

## 🚀 5分钟快速体验新功能

### 前置条件
✅ 已安装依赖: `pip install -r requirements.txt`
✅ 配置好 `.env` 文件 (LLM API配置)

---

## 步骤1: 启动后端服务 (30秒)

```bash
cd rag_all_app
python backend/main.py
```

看到以下信息表示成功：
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

---

## 步骤2: 上传测试文档 (1分钟)

### 方式A: 使用Web界面
1. 新开终端，启动前端:
```bash
streamlit run frontend/app.py
```

2. 浏览器打开 http://localhost:8501
3. 左侧边栏点击"上传文档"
4. 选择任意PDF/TXT/MD文档
5. 点击"上传并处理"

### 方式B: 使用API
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@your_document.pdf"
```

---

## 步骤3: 测试新RAG技术 (3分钟)

### 🎯 方式A: Streamlit界面 (推荐)

1. 在左侧边栏找到 "⚙️ RAG配置"
2. 在"选择RAG技术"中勾选以下新技术：
   - ✨ Query Transformation (查询转换)
   - ✨ Adaptive RAG (自适应)
   - ✨ Self RAG (自我反思)

3. 在主界面输入测试问题，例如：
   ```
   人工智能对教育行业的影响和挑战是什么？
   ```

4. 点击"发送"，等待结果

5. 在右侧面板查看对比结果：
   - 每个技术的答案
   - 检索到的文档
   - 相似度分数

### 🎯 方式B: API测试

```bash
# 测试 Query Transformation RAG
curl -X POST "http://localhost:8000/api/v1/qa/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是人工智能？",
    "rag_techniques": ["query_transformation_rag"],
    "rag_config": {
      "transformation_type": "hybrid"
    },
    "top_k": 3
  }'

# 测试 Adaptive RAG
curl -X POST "http://localhost:8000/api/v1/qa/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "人工智能对就业的影响是什么？",
    "rag_techniques": ["adaptive_rag"],
    "top_k": 3
  }'

# 测试 Self RAG
curl -X POST "http://localhost:8000/api/v1/qa/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "什么是深度学习？",
    "rag_techniques": ["self_rag"],
    "rag_config": {
      "min_support_score": 1
    },
    "top_k": 3
  }'
```

### 🎯 方式C: Python测试脚本

```bash
python test_new_techniques.py
```

这个脚本会自动测试所有新技术的不同配置。

---

## 🎨 查看效果对比

### 在Streamlit界面中：

1. **答案对比**
   - 右侧面板显示每个技术的答案
   - 可以滚动查看完整内容
   - 对比答案的详细程度和准确性

2. **检索文档对比**
   - 查看每个技术检索到的文档
   - 对比相似度分数
   - 展开查看文档内容

3. **评分功能**
   - 为每个答案打分 (1-5星)
   - 系统自动保存评分
   - 后续可用于效果分析

### 查看后端日志：

后端终端会显示详细的处理过程：

```
[Query Transform] 查询重写: 什么是AI → 人工智能的定义、核心概念和技术原理
[Query Transform] 查询分解: 3个子查询
[Adaptive RAG] 查询分类: Factual
[Adaptive RAG-Factual] 优化查询完成
[Self RAG] 检索决策: True
[Self RAG] 相关性评估: 3/5 个文档相关
[Self RAG] 候选1: 支持=fully, 效用=4/5, 总分=19
```

---

## 🎯 推荐测试用例

### 用例1: 简单事实性问题
```
查询: "什么是机器学习？"

预期效果:
- Query Transformation: 生成详细查询
- Adaptive RAG: 识别为Factual，使用精确检索
- Self RAG: 判断需要检索，选择最佳答案
```

### 用例2: 复杂分析性问题
```
查询: "人工智能对医疗行业的影响、机遇和挑战分别是什么？"

预期效果:
- Query Transformation: 分解为3-4个子查询
- Adaptive RAG: 识别为Analytical，使用子问题策略
- Self RAG: 评估多个候选答案
```

### 用例3: 观点性问题
```
查询: "如何看待自动驾驶的发展前景？"

预期效果:
- Adaptive RAG: 识别为Opinion，平衡多方观点
- Self RAG: 可能判断不需要检索
```

### 用例4: 上下文型问题
```
查询: "我想转行做AI工程师，应该如何学习？"

预期效果:
- Adaptive RAG: 识别为Contextual，推断背景
- Self RAG: 结合文档和模型知识
```

---

## 📊 性能观察要点

### 1. Query Transformation RAG
**关注点**:
- [ ] 是否生成了转换后的查询？
- [ ] 转换策略是否合理？
- [ ] 检索结果是否更相关？

**日志关键词**:
```
[Query Transform] 优化查询
[Query Transform] 查询分解
```

### 2. Adaptive RAG
**关注点**:
- [ ] 查询分类是否准确？
- [ ] 选择的策略是否合适？
- [ ] 不同类型的处理是否不同？

**日志关键词**:
```
[Adaptive RAG] 查询分类: Factual/Analytical/Opinion/Contextual
[Adaptive RAG-Factual] 优化查询
[Adaptive RAG-Analytical] 生成 3 个子问题
```

### 3. Self RAG
**关注点**:
- [ ] 检索决策是否合理？
- [ ] 相关性过滤是否有效？
- [ ] 答案评分是否准确？

**日志关键词**:
```
[Self RAG] 检索决策: True/False
[Self RAG] 相关性评估
[Self RAG] 候选1: 支持=fully, 效用=4/5, 总分=19
```

---

## 🔧 常见问题排查

### Q: 后端启动失败
**检查**:
1. 是否安装了所有依赖？
   ```bash
   pip install -r requirements.txt
   ```
2. `.env` 文件是否配置正确？
   ```bash
   cat .env  # 检查配置
   ```
3. 端口8000是否被占用？
   ```bash
   lsof -i :8000  # macOS/Linux
   ```

### Q: 查询超时或很慢
**原因**: 新技术涉及多次LLM调用

**解决**:
1. 使用更快的模型 (如GPT-3.5-turbo)
2. 减少top_k参数
3. 单独测试而非对比多个技术
4. 检查LLM API是否正常

### Q: 答案质量不理想
**调整**:
1. **Query Transformation**: 尝试不同的transformation_type
2. **Adaptive RAG**: 查看分类是否准确，可能需要更多文档
3. **Self RAG**: 调整min_support_score阈值

### Q: 找不到相关文档
**检查**:
1. 是否上传了文档？
2. 文档是否成功处理？
3. 查询是否与文档内容相关？
4. 尝试增加top_k参数

---

## 📈 下一步

### 深入了解
📖 阅读 [NEW_TECHNIQUES_GUIDE.md](NEW_TECHNIQUES_GUIDE.md) - 详细技术说明
📖 阅读 [CHANGELOG_V1.2.md](CHANGELOG_V1.2.md) - 完整更新日志

### 性能优化
⚙️ 调整配置参数
⚙️ 测试不同的LLM模型
⚙️ 优化chunk大小和overlap

### 评估对比
📊 使用评分功能
📊 导出评估结果
📊 分析性能指标

### 进阶使用
🔧 自定义system_prompt
🔧 集成到你的应用
🔧 扩展新的RAG技术

---

## 💡 最佳实践

1. **从Simple RAG开始**: 先建立基准
2. **逐个测试新技术**: 理解每个技术的特点
3. **记录对比结果**: 使用评分功能
4. **根据场景选择**: 没有最好的技术，只有最合适的
5. **查看日志**: 理解背后的处理过程

---

## 🎉 完成！

恭喜你完成了V1.2的快速体验！

现在你可以：
- ✅ 使用3个新的高级RAG技术
- ✅ 对比不同技术的效果
- ✅ 根据场景选择最佳策略

**继续探索更多功能，祝使用愉快！** 🚀

