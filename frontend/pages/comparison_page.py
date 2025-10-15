"""
RAG对比页面 - Page 2
包含：历史消息、对话窗口、详细RAG结果Tab
"""
import streamlit as st


def render_comparison_page():
    """
    RAG对比页面布局：
    ┌──────┬───────────────────────────────┐
    │历史  │ RAG技术Tab切换                 │
    │消息  ├─────────────┬─────────────────┤
    │      │ 答案展现     │ 文档&日志Tab    │
    │      ├─────────────┴─────────────────┤
    │      │ 当前问题 / 评估结果            │
    └──────┴───────────────────────────────┘
    """
    
    if not st.session_state.rag_results:
        st.info("💡 暂无对比结果，请先在「主页面」进行提问")
        return
    
    # 两栏布局：左侧历史消息 + 右侧RAG对比区
    col_history, col_rag = st.columns([2, 8])
    
    # ========== 左侧：历史消息 ==========
    with col_history:
        render_history_panel()
    
    # ========== 右侧：RAG对比区 ==========
    with col_rag:
        render_rag_comparison_area()


def render_history_panel():
    """左侧历史消息面板"""
    st.markdown("### 📜 历史消息")
    
    if not st.session_state.messages:
        st.caption("暂无历史消息")
        return
    
    # 显示消息列表（紧凑）
    history_container = st.container(height=700)
    
    with history_container:
        for i, message in enumerate(st.session_state.messages):
            role_icon = "👤" if message["role"] == "user" else "🤖"
            timestamp = message.get("timestamp", "")
            content_preview = message["content"][:30] + "..." if len(message["content"]) > 30 else message["content"]
            
            with st.expander(f"{role_icon} {timestamp}", expanded=False):
                st.markdown(message["content"])
    
    # 底部统计
    user_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    assistant_count = sum(1 for m in st.session_state.messages if m["role"] == "assistant")
    
    st.caption(f"💬 {user_count} 问 | {assistant_count} 答")


def render_rag_comparison_area():
    """右侧RAG对比区域"""
    
    # ========== 顶部：RAG技术Tab切换 ==========
    st.markdown("### 📊 RAG技术对比")
    
    tabs = st.tabs([f"{r['rag_technique']}" for r in st.session_state.rag_results])
    
    for i, (tab, result) in enumerate(zip(tabs, st.session_state.rag_results)):
        with tab:
            # ========== 上部：答案展现（左）+ 文档&日志（右）==========
            col_left, col_right = st.columns([6, 4])
            
            with col_left:
                # 答案展现
                st.markdown("#### 📝 答案")
                answer_container = st.container(height=500)  # 加长答案区域
                with answer_container:
                    st.markdown(result["answer"])
                
                st.markdown("---")
                
                # 当前问题
                if st.session_state.messages:
                    last_user_msg = next(
                        (m for m in reversed(st.session_state.messages) if m["role"] == "user"),
                        None
                    )
                    if last_user_msg:
                        st.markdown(f"**📌 当前问题:** {last_user_msg['content']}")
                
                # 评估结果
                st.markdown("**📊 评估结果:**")
                render_evaluation_summary(result, i)
            
            with col_right:
                # 文档和日志Tab
                doc_log_tabs = st.tabs(["📄 检索文档", "📋 执行日志"])
                
                # Tab 1: 检索文档（带分页）
                with doc_log_tabs[0]:
                    render_retrieved_docs_paginated(result, i)
                
                # Tab 2: 执行日志（新格式）
                with doc_log_tabs[1]:
                    render_execution_logs_new(result.get("metadata", {}))


def render_retrieved_docs_paginated(result: dict, result_index: int):
    """渲染检索文档（带分页）"""
    retrieved_docs = result.get("retrieved_docs", [])
    
    if not retrieved_docs:
        st.caption("无检索文档")
        return
    
    # 初始化当前页码
    page_key = f"doc_page_{result_index}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    
    current_page = st.session_state[page_key]
    total_docs = len(retrieved_docs)
    
    # 分页控制
    col_prev, col_pages, col_next = st.columns([1, 3, 1])
    
    with col_prev:
        if st.button("◀ 上一个", key=f"prev_{result_index}", disabled=current_page == 0):
            st.session_state[page_key] = max(0, current_page - 1)
            st.rerun()
    
    with col_pages:
        # 显示页码
        page_nums = []
        for p in range(total_docs):
            if p == current_page:
                page_nums.append(f"**[{p+1}]**")
            else:
                page_nums.append(f"{p+1}")
        st.markdown(" ".join(page_nums), unsafe_allow_html=True)
    
    with col_next:
        if st.button("下一个 ▶", key=f"next_{result_index}", disabled=current_page >= total_docs - 1):
            st.session_state[page_key] = min(total_docs - 1, current_page + 1)
            st.rerun()
    
    st.markdown("---")
    
    # 显示当前文档
    if 0 <= current_page < total_docs:
        doc = retrieved_docs[current_page]
        st.markdown(f"**文档 {current_page + 1}/{total_docs}** - 得分: `{doc.get('score', 0):.3f}`")
        
        doc_container = st.container(height=600)
        with doc_container:
            st.markdown(doc.get("content", ""))
            st.caption(f"📄 来源: {doc.get('metadata', {}).get('source', 'unknown')}")


def render_retrieved_docs(result: dict):
    """渲染检索文档（旧版，保留兼容）"""
    retrieved_docs = result.get("retrieved_docs", [])
    
    if not retrieved_docs:
        st.caption("无检索文档")
        return
    
    docs_container = st.container(height=300)
    with docs_container:
        for i, doc in enumerate(retrieved_docs[:5]):  # 只显示前5个
            st.markdown(f"**Doc {i+1}** `{doc.get('score', 0):.3f}`")
            content = doc.get("content", "")
            st.text(content[:150] + "..." if len(content) > 150 else content)
            st.caption(f"📄 {doc.get('metadata', {}).get('source', 'unknown')}")
            if i < len(retrieved_docs) - 1:
                st.markdown("---")


def render_execution_logs_new(metadata: dict):
    """渲染执行日志（新格式）"""
    logs = metadata.get("execution_logs", [])
    timing = metadata.get("timing", {})
    
    if not logs:
        st.caption("无执行日志")
        return
    
    # 顶部一行显示时间统计
    if timing:
        st.markdown(f"**总耗时**: {timing.get('total', 0):.3f}s  |  **检索**: {timing.get('retrieve', 0):.3f}s  |  **生成**: {timing.get('generate', 0):.3f}s")
        st.markdown("---")
    
    # 日志内容
    log_container = st.container(height=600)
    with log_container:
        for log in logs:
            timestamp = log["timestamp"].split("T")[1].split(".")[0]
            step = log["step"]
            message = log["message"]
            details = log.get("details", {})
            
            icon_map = {
                "init": "🚀", "retrieve_start": "🔍", "retrieve_end": "✅",
                "generate_start": "💭", "generate_end": "✅", "complete": "🎉"
            }
            icon = icon_map.get(step, "•")
            
            st.markdown(f"{icon} `{timestamp}` **{step}**")
            st.caption(f"   {message}")
            
            if details:
                details_text = " | ".join([f"{k}: {v}" for k, v in details.items()])
                st.caption(f"   └─ {details_text}")


def render_execution_logs_compact(metadata: dict):
    """渲染执行日志（紧凑版）"""
    logs = metadata.get("execution_logs", [])
    timing = metadata.get("timing", {})
    
    if not logs:
        st.caption("无执行日志")
        return
    
    # 时间统计
    if timing:
        st.metric("⏱️ 总耗时", f"{timing.get('total', 0):.3f}s")
        st.caption(f"检索: {timing.get('retrieve', 0):.3f}s | 生成: {timing.get('generate', 0):.3f}s")
        st.markdown("---")
    
    # 日志列表（紧凑）
    log_container = st.container(height=200)
    with log_container:
        for log in logs:
            timestamp = log["timestamp"].split("T")[1].split(".")[0]
            step = log["step"]
            message = log["message"]
            
            icon_map = {
                "init": "🚀", "retrieve_start": "🔍", "retrieve_end": "✅",
                "generate_start": "💭", "generate_end": "✅", "complete": "🎉"
            }
            icon = icon_map.get(step, "•")
            
            st.caption(f"{icon} `{timestamp}` {message}")


def render_evaluation_summary(result: dict, index: int):
    """渲染评估结果摘要"""
    eval_col1, eval_col2, eval_col3 = st.columns(3)
    
    with eval_col1:
        st.metric("⏱️ 执行时间", f"{result['execution_time']:.2f}s")
    
    with eval_col2:
        if "eval_results" in st.session_state and index in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[index]
            if eval_result.get("evaluation_success"):
                overall_score = eval_result.get("llm_evaluation", {}).get("overall_score", 0)
                st.metric("🎯 综合得分", f"{overall_score:.1f}/10")
            else:
                st.caption("❌ 评估失败")
        else:
            st.caption("⏳ 未评估")
    
    with eval_col3:
        if "eval_results" in st.session_state and index in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[index]
            if eval_result.get("ragas_evaluation"):
                ragas_score = eval_result["ragas_evaluation"].get("faithfulness", 0)
                st.metric("📈 忠实度", f"{ragas_score:.2f}")
            else:
                st.caption("⏸️ 无Ragas")
        else:
            st.caption("⏸️ 无Ragas")

