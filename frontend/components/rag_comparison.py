import streamlit as st
import requests
import pandas as pd

API_BASE_URL = "http://localhost:8000/api/v1"


def render_rag_comparison():
    """渲染右侧RAG结果对比面板"""
    
    st.header("📊 RAG结果对比")
    
    if not st.session_state.rag_results:
        st.info("暂无对比结果，请在对话窗口提问")
        return
    
    # 创建标签页
    tabs = st.tabs([f"{r['rag_technique']}" for r in st.session_state.rag_results])
    
    for i, (tab, result) in enumerate(zip(tabs, st.session_state.rag_results)):
        with tab:
            # 答案
            st.subheader("📝 答案")
            st.markdown(result["answer"])
            
            # 执行时间
            st.metric("⏱️ 执行时间", f"{result['execution_time']:.2f}秒")
            
            st.markdown("---")
            
            # 检索文档
            st.subheader("🔍 检索到的文档")
            
            for j, doc in enumerate(result["retrieved_docs"]):  # 显示前5个
                with st.expander(f"文档 {j+1} (相似度: {doc['score']:.4f})", expanded=(j==0)):
                    st.text_area(
                        "内容",
                        doc["content"],
                        height=150,
                        key=f"doc_{i}_{j}",
                        disabled=True
                    )
                    
                    if doc.get("metadata"):
                        st.caption(f"来源: {doc['metadata'].get('filename', 'Unknown')}")
            
            st.markdown("---")
            
            # 评分
            st.subheader("⭐ 评分")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                accuracy = st.slider(
                    "准确性",
                    0.0, 10.0, 5.0, 0.5,
                    key=f"acc_{i}"
                )
                relevance = st.slider(
                    "相关性",
                    0.0, 10.0, 5.0, 0.5,
                    key=f"rel_{i}"
                )
            
            with col_b:
                fluency = st.slider(
                    "流畅性",
                    0.0, 10.0, 5.0, 0.5,
                    key=f"flu_{i}"
                )
                completeness = st.slider(
                    "完整性",
                    0.0, 10.0, 5.0, 0.5,
                    key=f"com_{i}"
                )
            
            overall = st.slider(
                "总体评分",
                0.0, 10.0, 5.0, 0.5,
                key=f"overall_{i}"
            )
            
            comments = st.text_area(
                "评价说明",
                key=f"comments_{i}",
                placeholder="请输入您的评价..."
            )
            
            if st.button("提交评分", key=f"submit_{i}"):
                # TODO: 获取对应的qa_record_id
                # 这里需要在查询时保存qa_record_id
                st.warning("评分功能开发中...")
    
    st.markdown("---")
    
    # 统计对比
    st.subheader("📈 统计对比")
    
    try:
        response = requests.get(f"{API_BASE_URL}/evaluation/stats/comparison")
        if response.status_code == 200:
            stats = response.json()
            
            if stats:
                df = pd.DataFrame(stats)
                
                # 显示表格
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # 可视化
                col1, col2 = st.columns(2)
                
                with col1:
                    st.bar_chart(
                        df.set_index("technique")["avg_execution_time"],
                        use_container_width=True
                    )
                    st.caption("平均执行时间对比")
                
                with col2:
                    st.bar_chart(
                        df.set_index("technique")["avg_overall_score"],
                        use_container_width=True
                    )
                    st.caption("平均评分对比")
            else:
                st.info("暂无统计数据")
    except Exception as e:
        st.error(f"获取统计数据失败: {str(e)}")

