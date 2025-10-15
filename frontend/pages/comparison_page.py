"""
RAG对比页面 - Page 2
包含：历史消息、对话窗口、详细RAG结果Tab
"""
import streamlit as st


def render_comparison_page():
    """
    RAG对比页面布局：
    - 左侧：历史消息列表
    - 中间：当前对话
    - 右侧：不同RAG技术的详细结果Tab
    """
    
    if not st.session_state.rag_results:
        st.info("💡 暂无对比结果，请先在「主页面」进行提问")
        return
    
    # 三栏布局
    col1, col2, col3 = st.columns([2, 4, 4])
    
    # ========== 左侧：历史消息 ==========
    with col1:
        render_history_panel()
    
    # ========== 中间：多轮对话 ==========
    with col2:
        render_conversation_panel()
    
    # ========== 右侧：RAG结果Tab ==========
    with col3:
        render_rag_tabs()


def render_history_panel():
    """左侧历史消息面板"""
    st.markdown("### 📜 历史消息")
    
    if not st.session_state.messages:
        st.caption("暂无历史消息")
        return
    
    # 显示消息列表（紧凑）
    history_container = st.container(height=600)
    
    with history_container:
        for i, message in enumerate(st.session_state.messages):
            role_icon = "👤" if message["role"] == "user" else "🤖"
            timestamp = message.get("timestamp", "")
            content_preview = message["content"][:50] + "..." if len(message["content"]) > 50 else message["content"]
            
            with st.expander(f"{role_icon} {timestamp}", expanded=False):
                st.markdown(message["content"])
    
    # 底部统计
    user_count = sum(1 for m in st.session_state.messages if m["role"] == "user")
    assistant_count = sum(1 for m in st.session_state.messages if m["role"] == "assistant")
    
    st.caption(f"💬 {user_count} 个问题 | {assistant_count} 个回答")


def render_conversation_panel():
    """中间对话窗口面板"""
    st.markdown("### 💬 对话窗口")
    
    # 显示完整对话
    chat_container = st.container(height=600)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "timestamp" in message:
                    st.caption(message["timestamp"])
    
    # 最新问题提示
    if st.session_state.messages:
        last_user_msg = next(
            (m for m in reversed(st.session_state.messages) if m["role"] == "user"),
            None
        )
        if last_user_msg:
            st.info(f"📌 当前问题: {last_user_msg['content'][:100]}...")


def render_rag_tabs():
    """右侧RAG结果Tab"""
    st.markdown("### 📊 RAG技术对比")
    
    # 创建Tab
    tabs = st.tabs([f"{r['rag_technique']}" for r in st.session_state.rag_results])
    
    for i, (tab, result) in enumerate(zip(tabs, st.session_state.rag_results)):
        with tab:
            render_single_rag_result(result, i)


def render_single_rag_result(result: dict, index: int):
    """渲染单个RAG技术的详细结果"""
    
    # === 1. 答案内容 ===
    st.markdown("#### 📝 答案内容")
    answer_container = st.container(height=200)
    with answer_container:
        st.markdown(result["answer"])
    
    st.markdown("---")
    
    # === 2. 检索到的文档 ===
    with st.expander("📄 检索到的文档", expanded=False):
        retrieved_docs = result.get("retrieved_docs", [])
        if retrieved_docs:
            for i, doc in enumerate(retrieved_docs):
                st.markdown(f"**文档 {i+1}** (得分: {doc.get('score', 0):.3f})")
                st.text(doc.get("content", "")[:300] + "...")
                st.caption(f"来源: {doc.get('metadata', {}).get('source', 'unknown')}")
                st.markdown("---")
        else:
            st.caption("无检索文档")
    
    # === 3. 执行日志 ===
    if result.get("metadata", {}).get("execution_logs"):
        with st.expander("📋 执行日志", expanded=False):
            render_execution_logs(result["metadata"])
    
    # === 4. 评估结果 ===
    st.markdown("#### 📊 评估结果")
    
    eval_col1, eval_col2, eval_col3 = st.columns(3)
    
    with eval_col1:
        st.metric("⏱️ 执行时间", f"{result['execution_time']:.2f}s")
    
    with eval_col2:
        # 检查是否有评估结果
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
    
    # 详细评分
    if "eval_results" in st.session_state and index in st.session_state.eval_results:
        eval_result = st.session_state.eval_results[index]
        if eval_result.get("evaluation_success"):
            with st.expander("📈 详细评分", expanded=False):
                llm_eval = eval_result.get("llm_evaluation", {})
                
                # LLM评分
                st.markdown("**🤖 LLM评分**")
                scores = llm_eval.get("scores", {})
                for key, value in scores.items():
                    st.progress(value / 10, text=f"{key}: {value:.1f}/10")
                
                # Ragas评分
                if eval_result.get("ragas_evaluation"):
                    st.markdown("---")
                    st.markdown("**📊 Ragas评分**")
                    ragas_eval = eval_result["ragas_evaluation"]
                    for key, value in ragas_eval.items():
                        if isinstance(value, (int, float)):
                            st.progress(value, text=f"{key}: {value:.3f}")


def render_execution_logs(metadata: dict):
    """渲染执行日志"""
    logs = metadata.get("execution_logs", [])
    
    # 显示时间统计
    timing = metadata.get("timing", {})
    if timing:
        time_col1, time_col2, time_col3 = st.columns(3)
        with time_col1:
            st.metric("总耗时", f"{timing.get('total', 0):.3f}s")
        with time_col2:
            st.metric("检索", f"{timing.get('retrieve', 0):.3f}s")
        with time_col3:
            st.metric("生成", f"{timing.get('generate', 0):.3f}s")
        st.markdown("---")
    
    # 显示详细日志
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
        
        st.markdown(f"{icon} `{timestamp}` **{step}**: {message}")
        
        if details and step in ["retrieve_end", "generate_end", "complete"]:
            details_text = " | ".join([f"{k}: {v}" for k, v in details.items()])
            st.caption(f"    └─ {details_text}")

