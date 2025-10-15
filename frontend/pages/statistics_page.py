"""
统计分析页面 - Page 3
包含：对比表格、可视化图表、推荐、LLM生成分析报告
"""
import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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


def render_comparison_table():
    """渲染对比表格"""
    if not st.session_state.rag_results:
        st.caption("暂无数据")
        return
    
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
                
                if eval_result.get("ragas_evaluation"):
                    ragas_eval = eval_result["ragas_evaluation"]
                    row["Ragas忠实度"] = f"{ragas_eval.get('faithfulness', 0):.3f}"
                    row["Ragas相关性"] = f"{ragas_eval.get('answer_relevancy', 0):.3f}"
        
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
    
    # 准备数据
    techniques = [r["rag_technique"] for r in st.session_state.rag_results]
    exec_times = [r["execution_time"] for r in st.session_state.rag_results]
    
    # 提取评分数据
    overall_scores = []
    relevance_scores = []
    faithfulness_scores = []
    
    for i, result in enumerate(st.session_state.rag_results):
        if "eval_results" in st.session_state and i in st.session_state.eval_results:
            eval_result = st.session_state.eval_results[i]
            if eval_result.get("evaluation_success"):
                llm_eval = eval_result.get("llm_evaluation", {})
                
                # 使用正确的字段名：relevance_score, faithfulness_score
                overall_scores.append(llm_eval.get("overall_score", 0))
                relevance_scores.append(llm_eval.get("relevance_score", 0))
                faithfulness_scores.append(llm_eval.get("faithfulness_score", 0))
            else:
                overall_scores.append(0)
                relevance_scores.append(0)
                faithfulness_scores.append(0)
        else:
            overall_scores.append(0)
            relevance_scores.append(0)
            faithfulness_scores.append(0)
    
    # 三个图表
    viz_tab1, viz_tab2, viz_tab3 = st.tabs(["⏱️ 执行时间", "📊 LLM评分", "📈 性能对比"])
    
    with viz_tab1:
        # 执行时间柱状图
        df_time = pd.DataFrame({
            "RAG技术": techniques,
            "执行时间(秒)": exec_times
        })
        st.bar_chart(df_time.set_index("RAG技术"))
    
    with viz_tab2:
        # LLM评分对比
        if any(s > 0 for s in overall_scores):
            df_scores = pd.DataFrame({
                "RAG技术": techniques,
                "综合得分": overall_scores,
                "相关性": relevance_scores,
                "忠实度": faithfulness_scores
            })
            st.line_chart(df_scores.set_index("RAG技术"))
        else:
            st.info("请先进行批量评估")
    
    with viz_tab3:
        # 性能对比（散点图：执行时间 vs 综合得分）
        if any(s > 0 for s in overall_scores):
            df_perf = pd.DataFrame({
                "RAG技术": techniques,
                "执行时间": exec_times,
                "综合得分": overall_scores
            })
            st.scatter_chart(df_perf, x="执行时间", y="综合得分", size=20)
        else:
            st.info("请先进行批量评估")


def render_recommendations():
    """渲染推荐"""
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
                
                # 综合分数：质量(70%) + 速度(30%)
                time_score = max(0, 10 - exec_time)  # 时间越短得分越高
                combined_score = 0.7 * overall_score + 0.3 * time_score
                
                rankings.append({
                    "rag_technique": result["rag_technique"],
                    "overall_score": overall_score,
                    "exec_time": exec_time,
                    "combined_score": combined_score
                })
    
    if not rankings:
        st.warning("暂无有效评分")
        return
    
    # 排序
    rankings.sort(key=lambda x: x["combined_score"], reverse=True)
    
    # 显示Top 3
    st.markdown("#### 🏆 Top 3 推荐RAG技术")
    
    top3 = rankings[:3]
    
    cols = st.columns(3)
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (col, item) in enumerate(zip(cols, top3)):
        with col:
            st.markdown(f"### {medals[i]} {item['rag_technique']}")
            st.metric("综合评分", f"{item['combined_score']:.2f}/10")
            st.caption(f"质量: {item['overall_score']:.1f} | 速度: {item['exec_time']:.2f}s")


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

