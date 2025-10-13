import streamlit as st
import requests
import pandas as pd
import time

API_BASE_URL = "http://localhost:8000/api/v1"


def render_rag_comparison():
    """渲染右侧RAG结果对比面板"""
    
    st.header("📊 RAG结果对比")
    
    if not st.session_state.rag_results:
        st.info("暂无对比结果，请在对话窗口提问")
        return
    
    # 分成两个窗口：自动评估 和 统计对比
    
    # ========== 1. 自动评估窗口 ==========
    st.subheader("🤖 自动评估")
    
    # 批量评估按钮
    eval_config = st.session_state.get("eval_config", {"auto_eval_enabled": False, "use_ragas": False})
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🚀 批量评估所有RAG技术", type="primary", use_container_width=True):
            # 执行批量评估
            batch_evaluate_all()
    
    with col2:
        st.caption(f"LLM评估: ✅")
    
    with col3:
        ragas_status = "✅" if eval_config.get("use_ragas") else "❌"
        st.caption(f"Ragas: {ragas_status}")
    
    # 显示各个RAG技术的结果
    tabs = st.tabs([f"{r['rag_technique']}" for r in st.session_state.rag_results])
    
    for i, (tab, result) in enumerate(zip(tabs, st.session_state.rag_results)):
        with tab:
            # 答案
            st.markdown("**📝 答案**")
            st.markdown(result["answer"])
            
            # 执行时间
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("⏱️ 执行时间", f"{result['execution_time']:.2f}秒")
            with col_b:
                # 评估状态
                if "eval_results" in st.session_state and i in st.session_state.eval_results:
                    eval_result = st.session_state.eval_results[i]
                    if eval_result.get("evaluation_success"):
                        overall_score = eval_result.get("llm_evaluation", {}).get("overall_score", 0)
                        st.metric("🎯 综合得分", f"{overall_score:.1f}/10")
                    else:
                        st.caption("❌ 评估失败")
                else:
                    st.caption("⏳ 未评估")
            
            # 检索文档
            with st.expander(f"🔍 检索到的文档 ({len(result['retrieved_docs'])}个)", expanded=False):
                for j, doc in enumerate(result["retrieved_docs"][:5]):  # 最多显示5个
                    st.text_area(
                        f"文档 {j+1} (相似度: {doc['score']:.4f})",
                        doc["content"],
                        height=100,
                        key=f"doc_{i}_{j}",
                        disabled=True
                    )
            
            # 评估详情
            if "eval_results" in st.session_state and i in st.session_state.eval_results:
                eval_result = st.session_state.eval_results[i]
                
                if eval_result.get("evaluation_success"):
                    with st.expander("📊 详细评估结果", expanded=False):
                        # LLM评估
                        if eval_result.get("llm_evaluation"):
                            llm_eval = eval_result["llm_evaluation"]
                            
                            st.markdown("**LLM评分 (0-10)**")
                            cols = st.columns(6)
                            metrics_data = [
                                ("相关性", llm_eval.get('relevance_score', 0)),
                                ("忠实度", llm_eval.get('faithfulness_score', 0)),
                                ("连贯性", llm_eval.get('coherence_score', 0)),
                                ("流畅度", llm_eval.get('fluency_score', 0)),
                                ("简洁性", llm_eval.get('conciseness_score', 0)),
                                ("综合", llm_eval.get('overall_score', 0))
                            ]
                            
                            for col, (name, score) in zip(cols, metrics_data):
                                col.metric(name, f"{score:.1f}")
                            
                            if llm_eval.get("feedback"):
                                st.info(f"💡 {llm_eval['feedback']}")
                        
                        # Ragas评估
                        if eval_result.get("ragas_evaluation") and eval_result["ragas_evaluation"].get("evaluation_success"):
                            ragas_eval = eval_result["ragas_evaluation"]
                            scores = ragas_eval.get("scores", {})
                            
                            st.markdown("**Ragas评估 (0-1)**")
                            cols = st.columns(2)
                            
                            with cols[0]:
                                st.metric("Faithfulness", f"{scores.get('faithfulness', 0):.3f}")
                            with cols[1]:
                                st.metric("Answer Relevancy", f"{scores.get('answer_relevancy', 0):.3f}")
    
    st.markdown("---")
    
    # ========== 2. 统计对比窗口 ==========
    st.subheader("📈 统计对比")
    
    # 显示评估配置状态
    eval_config = st.session_state.get("eval_config", {"auto_eval_enabled": False, "use_ragas": False})
    col_status1, col_status2 = st.columns(2)
    with col_status1:
        llm_status = "✅ 已启用" if True else "❌ 未启用"
        st.caption(f"LLM评估: {llm_status}")
    with col_status2:
        ragas_status = "✅ 已启用" if eval_config.get("use_ragas", False) else "❌ 未启用"
        st.caption(f"Ragas评估: {ragas_status}")
    
    # 检查是否有评估结果
    if "eval_results" not in st.session_state or not st.session_state.eval_results:
        st.info("👆 点击上方「批量评估所有RAG技术」按钮查看统计对比")
        st.warning("💡 提示：如需Ragas评估，请在左侧「自动评估配置」中勾选「使用Ragas评估」，然后重新批量评估")
        return
    
    # 构建对比数据
    comparison_data = []
    
    for i, result in enumerate(st.session_state.rag_results):
        if i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            
            if eval_result.get("evaluation_success"):
                row_data = {
                    "RAG技术": result["rag_technique"],
                    "执行时间(秒)": result["execution_time"]
                }
                
                # LLM评分
                if eval_result.get("llm_evaluation"):
                    llm_eval = eval_result["llm_evaluation"]
                    row_data.update({
                        "相关性": llm_eval.get('relevance_score', 0),
                        "忠实度": llm_eval.get('faithfulness_score', 0),
                        "连贯性": llm_eval.get('coherence_score', 0),
                        "流畅度": llm_eval.get('fluency_score', 0),
                        "简洁性": llm_eval.get('conciseness_score', 0),
                        "综合得分": llm_eval.get('overall_score', 0)
                    })
                
                # Ragas评分
                if eval_result.get("ragas_evaluation") and eval_result["ragas_evaluation"].get("evaluation_success"):
                    ragas_eval = eval_result["ragas_evaluation"]
                    scores = ragas_eval.get("scores", {})
                    row_data.update({
                        "Ragas-Faithfulness": scores.get('faithfulness', 0),
                        "Ragas-Answer_Rel": scores.get('answer_relevancy', 0),
                    })
                
                # 检索质量
                final_scores = eval_result.get("final_scores", {})
                if final_scores:
                    row_data.update({
                        "检索精确度": final_scores.get('retrieval_precision', 0),
                        "上下文相关性": final_scores.get('context_relevance', 0)
                    })
                
                comparison_data.append(row_data)
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        
        # 显示表格
        st.markdown("#### 📊 详细对比表")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "RAG技术": st.column_config.TextColumn("RAG技术", width="medium"),
                "执行时间(秒)": st.column_config.NumberColumn("执行时间(秒)", format="%.2f"),
                "相关性": st.column_config.NumberColumn("相关性", format="%.1f"),
                "忠实度": st.column_config.NumberColumn("忠实度", format="%.1f"),
                "连贯性": st.column_config.NumberColumn("连贯性", format="%.1f"),
                "流畅度": st.column_config.NumberColumn("流畅度", format="%.1f"),
                "简洁性": st.column_config.NumberColumn("简洁性", format="%.1f"),
                "综合得分": st.column_config.NumberColumn("综合得分", format="%.1f"),
                "Ragas-Faithfulness": st.column_config.NumberColumn("Ragas-Faithfulness", format="%.3f"),
                "Ragas-Answer_Rel": st.column_config.NumberColumn("Ragas-Answer_Rel", format="%.3f"),
                "检索精确度": st.column_config.NumberColumn("检索精确度", format="%.2f"),
                "上下文相关性": st.column_config.NumberColumn("上下文相关性", format="%.1f"),
            }
        )
        
        # 可视化对比
        st.markdown("#### 📊 可视化对比")
        
        tab1, tab2, tab3 = st.tabs(["LLM评分对比", "Ragas对比", "性能对比"])
        
        with tab1:
            # LLM评分对比
            llm_metrics = ["相关性", "忠实度", "连贯性", "流畅度", "简洁性", "综合得分"]
            available_metrics = [m for m in llm_metrics if m in df.columns]
            
            if available_metrics:
                chart_data = df.set_index("RAG技术")[available_metrics]
                st.bar_chart(chart_data, use_container_width=True)
                
                # 显示最优技术
                best_tech = df.loc[df["综合得分"].idxmax(), "RAG技术"]
                best_score = df["综合得分"].max()
                st.success(f"🏆 综合得分最高: **{best_tech}** ({best_score:.1f}/10)")
        
        with tab2:
            # Ragas对比
            ragas_metrics = ["Ragas-Faithfulness", "Ragas-Answer_Rel"]
            available_ragas = [m for m in ragas_metrics if m in df.columns]
            
            if available_ragas:
                chart_data = df.set_index("RAG技术")[available_ragas]
                st.bar_chart(chart_data, use_container_width=True)
                
                # 显示Ragas最优
                if "Ragas-Faithfulness" in df.columns:
                    best_faith_tech = df.loc[df["Ragas-Faithfulness"].idxmax(), "RAG技术"]
                    best_faith = df["Ragas-Faithfulness"].max()
                    st.info(f"🎯 Faithfulness最高: **{best_faith_tech}** ({best_faith:.3f})")
                
                if "Ragas-Answer_Rel" in df.columns:
                    best_rel_tech = df.loc[df["Ragas-Answer_Rel"].idxmax(), "RAG技术"]
                    best_rel = df["Ragas-Answer_Rel"].max()
                    st.info(f"🎯 Answer Relevancy最高: **{best_rel_tech}** ({best_rel:.3f})")
            else:
                st.warning("📊 未启用Ragas评估")
                st.info("""
                    💡 如需启用Ragas标准化评估：
                    
                    1. 前往左侧栏「🤖 自动评估配置」
                    2. ☑️ 勾选「使用Ragas评估」
                    3. 返回此页面，点击「🚀 批量评估所有RAG技术」
                    
                    ⏱️ 注意：Ragas评估会增加评估时间（~5-8秒/RAG）
                """)
        
        with tab3:
            # 性能对比
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**执行时间对比**")
                time_chart = df.set_index("RAG技术")["执行时间(秒)"]
                st.bar_chart(time_chart, use_container_width=True)
                
                fastest = df.loc[df["执行时间(秒)"].idxmin(), "RAG技术"]
                fastest_time = df["执行时间(秒)"].min()
                st.caption(f"⚡ 最快: {fastest} ({fastest_time:.2f}秒)")
            
            with col2:
                if "检索精确度" in df.columns:
                    st.markdown("**检索质量对比**")
                    retrieval_chart = df.set_index("RAG技术")["检索精确度"]
                    st.bar_chart(retrieval_chart, use_container_width=True)
                    
                    best_retrieval = df.loc[df["检索精确度"].idxmax(), "RAG技术"]
                    best_ret_score = df["检索精确度"].max()
                    st.caption(f"🎯 最优: {best_retrieval} ({best_ret_score:.2f})")
        
        # 推荐
        st.markdown("#### 💡 推荐")
        
        # 综合评分前3
        top3 = df.nlargest(3, "综合得分")[["RAG技术", "综合得分", "执行时间(秒)"]]
        st.markdown("**综合评分Top 3:**")
        for idx, row in top3.iterrows():
            st.write(f"🥇 **{row['RAG技术']}** - 得分: {row['综合得分']:.1f}/10, 耗时: {row['执行时间(秒)']:.2f}秒")
    
    else:
        st.warning("评估数据不完整，请重新评估")


def batch_evaluate_all():
    """批量评估所有RAG技术"""
    
    eval_config = st.session_state.get("eval_config", {"auto_eval_enabled": True, "use_ragas": False})
    use_ragas = eval_config.get("use_ragas", False)
    
    # 收集所有qa_record_id
    qa_record_ids = []
    for result in st.session_state.rag_results:
        if result.get("qa_record_id"):
            qa_record_ids.append(result["qa_record_id"])
    
    if not qa_record_ids:
        st.error("无法获取QA记录ID，请重新查询")
        return
    
    # 显示进度
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        # 初始化评估结果
        if "eval_results" not in st.session_state:
            st.session_state.eval_results = {}
        
        # 逐个评估
        for i, qa_id in enumerate(qa_record_ids):
            status_text.text(f"正在评估 {i+1}/{len(qa_record_ids)}: {st.session_state.rag_results[i]['rag_technique']}")
            
            try:
                response = requests.post(
                    f"{API_BASE_URL}/evaluation/auto",
                    json={
                        "qa_record_id": qa_id,
                        "use_llm_evaluator": True,
                        "use_ragas": use_ragas,
                        "reference_answer": None
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    eval_result = response.json()
                    if eval_result.get("evaluation_success"):
                        st.session_state.eval_results[i] = eval_result
                    else:
                        st.warning(f"评估失败: {st.session_state.rag_results[i]['rag_technique']}")
                else:
                    st.warning(f"API错误: {response.status_code}")
                    
            except Exception as e:
                st.warning(f"评估出错: {str(e)}")
            
            # 更新进度
            progress_bar.progress((i + 1) / len(qa_record_ids))
            time.sleep(0.5)  # 避免请求过快
        
        status_text.text("✅ 评估完成!")
        time.sleep(1)
        status_text.empty()
        progress_bar.empty()
        
        st.success(f"✅ 成功评估 {len(st.session_state.eval_results)}/{len(qa_record_ids)} 个RAG技术")
        st.rerun()
        
    except Exception as e:
        st.error(f"批量评估失败: {str(e)}")
        progress_bar.empty()
        status_text.empty()
