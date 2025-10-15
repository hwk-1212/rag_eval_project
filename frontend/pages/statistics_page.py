"""
统计分析页面 - Page 3
包含：对比表格、可视化图表、推荐、LLM生成分析报告
"""
import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from loguru import logger

API_BASE_URL = "http://localhost:8000/api/v1"


def render_statistics_page():
    """
    统计分析页面布局：
    ┌──────────────────────────┐
    │ 评估按钮                  │
    ├──────────────┬───────────┤
    │ 对比表格      │ 可视化    │
    ├──────────────┴───────────┤
    │ 推荐                      │
    ├───────────────────────────┤
    │ AI 分析报告               │
    └───────────────────────────┘
    """
    
    if not st.session_state.rag_results:
        st.info("💡 暂无统计数据，请先在「主页面」进行提问")
        return
    
    st.markdown("## 📈 统计分析与对比")
    
    # ========== 1. 顶部：评估按钮 ==========
    eval_col1, eval_col2, eval_col3 = st.columns([3, 1, 1])
    
    with eval_col1:
        if st.button("🚀 批量评估所有RAG技术", type="primary", use_container_width=True, key="batch_eval"):
            with st.spinner("正在评估..."):
                batch_evaluate_all()
    
    with eval_col2:
        eval_config = st.session_state.get("eval_config", {})
        st.caption(f"LLM: ✅")
    
    with eval_col3:
        ragas_status = "✅" if eval_config.get("use_ragas") else "❌"
        st.caption(f"Ragas: {ragas_status}")
    
    st.markdown("---")
    
    # ========== 2. 中间：对比表格（左）+ 可视化（右）==========
    col_table, col_viz = st.columns([5, 5])
    
    with col_table:
        st.markdown("### 📊 对比表格")
        render_comparison_table()
    
    with col_viz:
        st.markdown("### 📉 可视化分析")
        render_visualizations()
    
    st.markdown("---")
    
    # ========== 3. 推荐 ==========
    st.markdown("### 💡 推荐")
    render_recommendations()
    
    st.markdown("---")
    
    # ========== 4. AI分析报告 ==========
    st.markdown("### 📝 AI分析报告")
    render_ai_report()


def batch_evaluate_all():
    """批量评估所有RAG技术（修复版）"""
    if not st.session_state.rag_results:
        st.warning("没有RAG结果可供评估")
        return
    
    eval_config = st.session_state.get("eval_config", {})
    use_ragas = eval_config.get("use_ragas", False)
    concurrent_num = st.session_state.get("concurrent_num", 3)
    
    # 初始化评估结果存储
    if "eval_results" not in st.session_state:
        st.session_state.eval_results = {}
    
    total = len(st.session_state.rag_results)
    completed = 0
    failed = 0
    
    # 显示评估信息
    eval_info = st.empty()
    eval_progress = st.empty()
    
    eval_info.info(f"🚀 开始批量评估 {total} 个RAG技术...")
    
    # 并发评估
    try:
        with ThreadPoolExecutor(max_workers=concurrent_num) as executor:
            future_to_index = {
                executor.submit(
                    evaluate_single_rag,
                    i,
                    result,
                    use_ragas
                ): i
                for i, result in enumerate(st.session_state.rag_results)
            }
            
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    eval_result = future.result()
                    st.session_state.eval_results[index] = eval_result
                    
                    if eval_result.get("evaluation_success"):
                        completed += 1
                    else:
                        failed += 1
                    
                    # 更新进度
                    progress = (completed + failed) / total
                    eval_progress.progress(progress, text=f"进度: {completed + failed}/{total}")
                    
                except Exception as e:
                    failed += 1
                    st.session_state.eval_results[index] = {
                        "evaluation_success": False,
                        "error": str(e)
                    }
        
        # 显示完成信息
        eval_info.success(f"🎉 评估完成！成功: {completed}, 失败: {failed}")
        eval_progress.empty()
        
        # 自动刷新页面显示结果
        time.sleep(1)
        st.rerun()
        
    except Exception as e:
        eval_info.error(f"❌ 评估过程出错: {str(e)}")
        eval_progress.empty()


def evaluate_single_rag(index: int, result: dict, use_ragas: bool) -> dict:
    """评估单个RAG技术"""
    # qa_record_id是result的直接字段，不在metadata中
    qa_record_id = result.get("qa_record_id")
    
    if not qa_record_id:
        return {"evaluation_success": False, "error": f"缺少qa_record_id，result keys: {list(result.keys())}"}
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/evaluation/auto",
            json={
                "qa_record_id": qa_record_id,
                "use_llm": True,
                "use_ragas": use_ragas
            },
            timeout=180
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"evaluation_success": False, "error": response.text}
    
    except Exception as e:
        return {"evaluation_success": False, "error": str(e)}


def load_evaluations_from_db():
    """从数据库加载评估数据"""
    if not st.session_state.rag_results:
        return
    
    try:
        # 为每个RAG结果加载数据库中的评估数据
        for i, result in enumerate(st.session_state.rag_results):
            qa_record_id = result.get("qa_record_id")
            if not qa_record_id:
                continue
            
            # 调用API获取评估数据（使用全局常量）
            response = requests.get(
                f"{API_BASE_URL}/evaluations/qa_record/{qa_record_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                evaluations = response.json()
                if evaluations:
                    # 获取最新的auto类型评估
                    auto_evals = [e for e in evaluations if e.get("score_type") == "auto"]
                    if auto_evals:
                        latest_eval = auto_evals[-1]  # 最新的评估
                        
                        # 初始化eval_results字典
                        if "eval_results" not in st.session_state:
                            st.session_state.eval_results = {}
                        
                        # 构造eval_result格式
                        eval_result = {
                            "evaluation_success": True,
                            "llm_evaluation": {
                                "overall_score": latest_eval.get("overall_score", 0),
                                "relevance_score": latest_eval.get("relevance_score", 0),
                                "faithfulness_score": latest_eval.get("faithfulness_score", 0),
                                "coherence_score": latest_eval.get("coherence_score", 0),
                                "fluency_score": latest_eval.get("fluency_score", 0),
                                "conciseness_score": latest_eval.get("conciseness_score", 0),
                            }
                        }
                        
                        # 从metadata中提取Ragas评分
                        metadata = latest_eval.get("meta_data") or latest_eval.get("metadata", {})
                        if metadata and "ragas_scores" in metadata:
                            ragas_scores = metadata["ragas_scores"]
                            eval_result["ragas_evaluation"] = {
                                "faithfulness": ragas_scores.get("faithfulness", 0),
                                "answer_relevancy": ragas_scores.get("answer_relevancy", 0),
                                "context_precision": ragas_scores.get("context_precision", 0),
                                "context_recall": ragas_scores.get("context_recall", 0),
                            }
                        
                        st.session_state.eval_results[i] = eval_result
    except Exception as e:
        logger.warning(f"从数据库加载评估数据失败: {e}")


def render_comparison_table():
    """渲染对比表格"""
    if not st.session_state.rag_results:
        st.caption("暂无数据")
        return
    
    # 尝试从数据库加载评估数据（如果session_state中没有）
    if "eval_results" not in st.session_state or not st.session_state.eval_results:
        load_evaluations_from_db()
    
    # 构建表格数据
    table_data = []
    
    for i, result in enumerate(st.session_state.rag_results):
        row = {
            "RAG技术": result["rag_technique"],
            "执行时间(s)": f"{result['execution_time']:.2f}",
            "综合得分": "-",
            "相关性": "-",
            "忠实度": "-",
            "连贯性": "-",
            "流畅性": "-",
            "简洁性": "-",
            "Ragas忠实度": "-",
            "Ragas相关性": "-"
        }
        
        # 添加评估结果
        if "eval_results" in st.session_state and i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            if eval_result.get("evaluation_success"):
                llm_eval = eval_result.get("llm_evaluation", {})
                
                # 后端返回的字段名是 relevance_score, faithfulness_score 等
                row["综合得分"] = f"{llm_eval.get('overall_score', 0):.1f}"
                row["相关性"] = f"{llm_eval.get('relevance_score', 0):.1f}"
                row["忠实度"] = f"{llm_eval.get('faithfulness_score', 0):.1f}"
                row["连贯性"] = f"{llm_eval.get('coherence_score', 0):.1f}"
                row["流畅性"] = f"{llm_eval.get('fluency_score', 0):.1f}"
                row["简洁性"] = f"{llm_eval.get('conciseness_score', 0):.1f}"
                
                if eval_result.get("ragas_evaluation"):
                    ragas_eval = eval_result["ragas_evaluation"]
                    # 只展示实际评估的Ragas指标（非零值）
                    faithfulness = ragas_eval.get('faithfulness', 0)
                    answer_relevancy = ragas_eval.get('answer_relevancy', 0)
                    if faithfulness > 0:
                        row["Ragas忠实度"] = f"{faithfulness:.3f}"
                    if answer_relevancy > 0:
                        row["Ragas相关性"] = f"{answer_relevancy:.3f}"
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    
    # 显示表格（带样式）
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # 下载按钮
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 下载CSV",
        data=csv,
        file_name="rag_comparison.csv",
        mime="text/csv"
    )


def render_visualizations():
    """渲染可视化图表"""
    if not st.session_state.rag_results:
        st.caption("暂无数据")
        return
    
    # 尝试从数据库加载评估数据（如果session_state中没有）
    if "eval_results" not in st.session_state or not st.session_state.eval_results:
        load_evaluations_from_db()
    
    # 准备数据
    techniques = [r["rag_technique"] for r in st.session_state.rag_results]
    exec_times = [r["execution_time"] for r in st.session_state.rag_results]
    
    # 提取评分数据 - 所有LLM评价维度
    overall_scores = []
    relevance_scores = []
    faithfulness_scores = []
    coherence_scores = []
    fluency_scores = []
    conciseness_scores = []
    
    for i, result in enumerate(st.session_state.rag_results):
        if "eval_results" in st.session_state and i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            if eval_result.get("evaluation_success"):
                llm_eval = eval_result.get("llm_evaluation", {})
                
                # 使用正确的字段名
                overall_scores.append(llm_eval.get("overall_score", 0))
                relevance_scores.append(llm_eval.get("relevance_score", 0))
                faithfulness_scores.append(llm_eval.get("faithfulness_score", 0))
                coherence_scores.append(llm_eval.get("coherence_score", 0))
                fluency_scores.append(llm_eval.get("fluency_score", 0))
                conciseness_scores.append(llm_eval.get("conciseness_score", 0))
            else:
                overall_scores.append(0)
                relevance_scores.append(0)
                faithfulness_scores.append(0)
                coherence_scores.append(0)
                fluency_scores.append(0)
                conciseness_scores.append(0)
        else:
            overall_scores.append(0)
            relevance_scores.append(0)
            faithfulness_scores.append(0)
            coherence_scores.append(0)
            fluency_scores.append(0)
            conciseness_scores.append(0)
    
    # 两个图表Tab
    viz_tab1, viz_tab2 = st.tabs(["📊 LLM评分对比", "📈 性能对比"])
    
    with viz_tab1:
        # LLM评分对比 - 堆叠柱状图
        if any(s > 0 for s in overall_scores):
            try:
                import plotly.graph_objects as go
                
                # 创建堆叠柱状图
                fig = go.Figure()
                
                # 添加每个评价维度
                fig.add_trace(go.Bar(
                    name='相关性',
                    x=techniques,
                    y=relevance_scores,
                    marker_color='#FF6B6B'
                ))
                
                fig.add_trace(go.Bar(
                    name='忠实度',
                    x=techniques,
                    y=faithfulness_scores,
                    marker_color='#4ECDC4'
                ))
                
                fig.add_trace(go.Bar(
                    name='连贯性',
                    x=techniques,
                    y=coherence_scores,
                    marker_color='#45B7D1'
                ))
                
                fig.add_trace(go.Bar(
                    name='流畅性',
                    x=techniques,
                    y=fluency_scores,
                    marker_color='#FFA07A'
                ))
                
                fig.add_trace(go.Bar(
                    name='简洁性',
                    x=techniques,
                    y=conciseness_scores,
                    marker_color='#98D8C8'
                ))
                
                # 更新布局
                fig.update_layout(
                    barmode='stack',
                    title='LLM评分维度对比（堆叠柱状图）',
                    xaxis_title='RAG技术',
                    yaxis_title='评分',
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except ImportError:
                st.error("⚠️ Plotly未安装，请运行: pip install plotly")
                st.info("或执行脚本: bash install_plotly.sh")
                # 降级到简单图表
                df_scores = pd.DataFrame({
                    "RAG技术": techniques,
                    "相关性": relevance_scores,
                    "忠实度": faithfulness_scores,
                    "连贯性": coherence_scores,
                    "流畅性": fluency_scores,
                    "简洁性": conciseness_scores
                })
                st.bar_chart(df_scores.set_index("RAG技术"))
        else:
            st.info("请先进行批量评估")
    
    with viz_tab2:
        # 性能对比 - 综合得分和执行时间的并列柱状图
        if any(s > 0 for s in overall_scores):
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                
                # 创建并列双Y轴子图
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('综合得分', '执行时间'),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                # 左图：综合得分
                fig.add_trace(
                    go.Bar(
                        x=techniques,
                        y=overall_scores,
                        name='综合得分',
                        marker_color='#667EEA',
                        text=[f'{s:.1f}' for s in overall_scores],
                        textposition='outside',
                        showlegend=False
                    ),
                    row=1, col=1
                )
                
                # 右图：执行时间
                fig.add_trace(
                    go.Bar(
                        x=techniques,
                        y=exec_times,
                        name='执行时间',
                        marker_color='#F093FB',
                        text=[f'{t:.2f}s' for t in exec_times],
                        textposition='outside',
                        showlegend=False
                    ),
                    row=1, col=2
                )
                
                # 更新布局
                fig.update_xaxes(title_text="RAG技术", row=1, col=1)
                fig.update_xaxes(title_text="RAG技术", row=1, col=2)
                fig.update_yaxes(title_text="得分（0-10）", range=[0, 10.5], row=1, col=1)
                fig.update_yaxes(title_text="时间（秒）", row=1, col=2)
                
                fig.update_layout(
                    title_text='性能对比：综合得分 vs 执行时间',
                    height=450,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except ImportError:
                st.error("⚠️ Plotly未安装，请运行: pip install plotly")
                st.info("或执行脚本: bash install_plotly.sh")
                # 降级到简单图表
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("##### 综合得分")
                    df_score = pd.DataFrame({
                        "RAG技术": techniques,
                        "得分": overall_scores
                    })
                    st.bar_chart(df_score.set_index("RAG技术"))
                
                with col2:
                    st.markdown("##### 执行时间")
                    df_time = pd.DataFrame({
                        "RAG技术": techniques,
                        "时间(秒)": exec_times
                    })
                    st.bar_chart(df_time.set_index("RAG技术"))
        else:
            st.info("请先进行批量评估")


def render_recommendations():
    """渲染推荐"""
    # 尝试从数据库加载评估数据（如果session_state中没有）
    if "eval_results" not in st.session_state or not st.session_state.eval_results:
        load_evaluations_from_db()
    
    if "eval_results" not in st.session_state or not st.session_state.eval_results:
        st.info("💡 请先进行批量评估以获取推荐")
        return
    
    # 计算Top 3
    rankings = []
    
    for i, result in enumerate(st.session_state.rag_results):
        if i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            if eval_result.get("evaluation_success"):
                llm_eval = eval_result.get("llm_evaluation", {})
                overall_score = llm_eval.get("overall_score", 0)
                exec_time = result["execution_time"]
                
                rankings.append({
                    "rag_technique": result["rag_technique"],
                    "overall_score": overall_score,
                    "exec_time": exec_time
                })
    
    if not rankings:
        st.warning("暂无有效评分")
        return
    
    # 排序（按overall_score排序）
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)
    
    # 显示Top 3
    st.markdown("#### 🏆 Top 3 推荐RAG技术")
    
    top3 = rankings[:3]
    
    cols = st.columns(3)
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (col, item) in enumerate(zip(cols, top3)):
        with col:
            st.markdown(f"### {medals[i]} {item['rag_technique']}")
            st.metric("综合评分", f"{item['overall_score']:.1f}/10")
            st.caption(f"执行时间: {item['exec_time']:.2f}s")


def render_ai_report():
    """渲染AI生成的分析报告"""
    if not st.session_state.rag_results:
        st.caption("暂无数据")
        return
    
    if st.button("✨ 生成AI分析报告", type="primary"):
        with st.spinner("🤖 AI正在分析..."):
            report = generate_ai_report()
            st.markdown(report)


def generate_ai_report() -> str:
    """生成AI分析报告（调用LLM）"""
    # 收集数据
    summary_data = []
    
    for i, result in enumerate(st.session_state.rag_results):
        item = {
            "技术": result["rag_technique"],
            "时间": result["execution_time"]
        }
        
        if "eval_results" in st.session_state and i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            if eval_result.get("evaluation_success"):
                llm_eval = eval_result.get("llm_evaluation", {})
                item["得分"] = llm_eval.get("overall_score", 0)
        
        summary_data.append(item)
    
    # 构建prompt
    prompt = f"""请分析以下RAG技术对比结果，生成一份专业的分析报告。

数据：
{summary_data}

要求：
1. 总结各RAG技术的优劣
2. 分析性能和质量的权衡
3. 给出应用场景建议
4. 提出改进方向

报告格式：Markdown
"""
    
    try:
        from backend.utils.llm import call_llm
        
        report = call_llm(
            messages=[
                {"role": "system", "content": "你是一个专业的RAG技术分析师"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return report
    
    except Exception as e:
        return f"生成报告失败：{str(e)}\n\n请确保后端服务正常运行。"

