# 数据库迁移指南 V1.8.7

## 概述

本迁移添加了3个新字段到`evaluations`表，用于完整保存LLM评估的所有维度：
- `faithfulness_score` (忠实度)
- `coherence_score` (连贯性)
- `conciseness_score` (简洁性)

## 快速开始

### 方法1：使用Python脚本（推荐）

```bash
cd rag_all_app
python3 migrate_database.py
```

### 方法2：使用Shell脚本

```bash
cd rag_all_app
chmod +x migrate.sh
./migrate.sh
```

## 详细步骤

### 1. 备份数据库（可选但推荐）

```bash
cp backend/data/rag_eval.db backend/data/rag_eval.db.backup
```

### 2. 执行迁移

```bash
python3 migrate_database.py
```

**预期输出：**
```
🚀 开始执行数据库迁移...
------------------------------------------------------------
开始迁移数据库: /path/to/backend/data/rag_eval.db
备份evaluations表数据...
当前evaluations表有 X 条记录
添加 faithfulness_score 字段...
✅ faithfulness_score 字段添加成功
添加 coherence_score 字段...
✅ coherence_score 字段添加成功
添加 conciseness_score 字段...
✅ conciseness_score 字段添加成功
验证迁移结果...
evaluations表当前字段:
  - id (INTEGER)
  - qa_record_id (INTEGER)
  - score_type (VARCHAR(50))
  - accuracy_score (REAL)
  - relevance_score (REAL)
  - faithfulness_score (REAL)     # 新增
  - coherence_score (REAL)        # 新增
  - fluency_score (REAL)
  - conciseness_score (REAL)      # 新增
  - completeness_score (REAL)
  - overall_score (REAL)
  - comments (TEXT)
  - evaluator (VARCHAR(100))
  - create_time (DATETIME)
  - metadata (JSON)
🎉 数据库迁移成功完成！
原有数据保留: X 条记录
------------------------------------------------------------
✅ 数据库迁移成功完成！

后续步骤:
1. 重启后端服务: cd backend && python main.py
2. 重启前端服务: streamlit run frontend/app.py
3. 测试评估功能，确认新字段正常保存
```

### 3. 重启服务

```bash
# 停止现有服务（Ctrl+C）

# 重启后端
cd backend
python main.py

# 新终端窗口，重启前端
cd rag_all_app
streamlit run frontend/app.py
```

### 4. 验证迁移

访问统计分析页面，应该能看到：
- ✅ 对比表格显示完整的评分数据
- ✅ 相关性、忠实度、连贯性都有值
- ✅ 可视化图表正确显示评分曲线
- ✅ 推荐排序正确

## 自动加载功能

### 新功能说明

**V1.8.8 新增**：前端自动从数据库加载历史评估数据

#### 工作原理

当你访问统计分析页面时：

1. **自动检测**：检查`session_state`中是否有评估数据
2. **自动加载**：如果没有，调用`load_evaluations_from_db()`
3. **API查询**：通过`/api/v1/evaluations/qa_record/{qa_record_id}`获取
4. **填充数据**：将数据库中的评估结果填充到`session_state`
5. **实时显示**：表格、可视化、推荐自动显示

#### 生效位置

- ✅ **对比表格**：`render_comparison_table()`
- ✅ **可视化图表**：`render_visualizations()`
- ✅ **推荐排序**：`render_recommendations()`

#### 用户体验改进

**之前**：必须重新进行批量评估才能看到数据
**现在**：页面自动加载历史评估，无需重新评估

## 故障排除

### 问题1：字段已存在

**症状**：
```
faithfulness_score 字段已存在，跳过
```

**解决**：这是正常的，说明字段已经添加过了。

### 问题2：数据库文件不存在

**症状**：
```
数据库文件不存在: backend/data/rag_eval.db
```

**解决**：
```bash
# 启动一次后端服务，自动创建数据库
cd backend
python main.py
```

### 问题3：数据库被占用

**症状**：
```
database is locked
```

**解决**：
1. 停止所有后端服务
2. 确认没有其他程序访问数据库
3. 重新执行迁移脚本

### 问题4：前端表格仍然不显示

**症状**：数据库有数据，但前端表格为空

**解决**：
1. 检查是否有`qa_record_id`
2. 清空浏览器缓存
3. 重启前端服务
4. 刷新页面（Ctrl+Shift+R）

**调试**：
```python
# 在浏览器控制台查看
st.session_state.rag_results
st.session_state.eval_results
```

## 回滚方案

如果迁移后出现问题，可以回滚：

```bash
# 恢复备份
cp backend/data/rag_eval.db.backup backend/data/rag_eval.db

# 重启服务
cd backend && python main.py
```

## 数据库Schema对比

### 迁移前
```sql
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY,
    qa_record_id INTEGER,
    score_type VARCHAR(50),
    accuracy_score REAL,
    relevance_score REAL,
    fluency_score REAL,
    completeness_score REAL,
    overall_score REAL,
    comments TEXT,
    evaluator VARCHAR(100),
    create_time DATETIME,
    metadata JSON
);
```

### 迁移后
```sql
CREATE TABLE evaluations (
    id INTEGER PRIMARY KEY,
    qa_record_id INTEGER,
    score_type VARCHAR(50),
    accuracy_score REAL,
    relevance_score REAL,
    faithfulness_score REAL,      -- 新增
    coherence_score REAL,          -- 新增
    fluency_score REAL,
    conciseness_score REAL,        -- 新增
    completeness_score REAL,
    overall_score REAL,
    comments TEXT,
    evaluator VARCHAR(100),
    create_time DATETIME,
    metadata JSON
);
```

## 技术细节

### 迁移策略

使用**ALTER TABLE ADD COLUMN**方式：
- ✅ 安全：不会丢失数据
- ✅ 快速：无需重建表
- ✅ 向后兼容：新字段允许NULL
- ✅ 幂等：可重复执行

### 字段说明

| 字段名 | 类型 | 说明 | 范围 |
|--------|------|------|------|
| `faithfulness_score` | REAL | 忠实度：答案是否基于检索内容 | 0-10 |
| `coherence_score` | REAL | 连贯性：答案逻辑是否连贯 | 0-10 |
| `conciseness_score` | REAL | 简洁性：答案是否简洁 | 0-10 |

### 自动加载逻辑

```python
def load_evaluations_from_db():
    """从数据库加载评估数据"""
    for i, result in enumerate(st.session_state.rag_results):
        qa_record_id = result.get("qa_record_id")
        
        # 调用API获取评估数据
        response = requests.get(
            f"{API_BASE_URL}/evaluations/qa_record/{qa_record_id}"
        )
        
        # 获取最新的auto类型评估
        auto_evals = [e for e in evaluations if e.get("score_type") == "auto"]
        latest_eval = auto_evals[-1]
        
        # 填充到session_state
        st.session_state.eval_results[i] = {
            "evaluation_success": True,
            "llm_evaluation": {
                "overall_score": latest_eval.get("overall_score", 0),
                "relevance_score": latest_eval.get("relevance_score", 0),
                "faithfulness_score": latest_eval.get("faithfulness_score", 0),
                "coherence_score": latest_eval.get("coherence_score", 0),
                ...
            }
        }
```

## 版本历史

- **V1.8.7** - 添加新字段到数据库模型和API
- **V1.8.8** - 添加迁移工具和前端自动加载功能

## 相关文档

- [自动评估指南](AUTO_EVALUATION_GUIDE.md)
- [批量评估快速开始](BATCH_EVAL_QUICKSTART.md)
- [README](README.md)

## 支持

如果遇到问题：
1. 查看上方的故障排除章节
2. 检查日志文件：`backend/logs/app_*.log`
3. 确认数据库文件存在且可读写
4. 验证API服务正常运行

