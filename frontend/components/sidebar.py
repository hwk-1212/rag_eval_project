import streamlit as st
import requests
from pathlib import Path

API_BASE_URL = "http://localhost:8000/api/v1"


def render_sidebar():
    """渲染左侧边栏 - 文件管理和配置"""
    
    # 初始化eval_config（如果不存在）
    if "eval_config" not in st.session_state:
        st.session_state.eval_config = {
            "auto_eval_enabled": False,  # 默认不自动评估
            "use_ragas": True  # 默认启用Ragas
        }
    
    # 初始化并发数（如果不存在）
    if "concurrent_num" not in st.session_state:
        st.session_state.concurrent_num = 3
    
    st.header("📁 文件管理")
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "上传文档",
        type=["pdf", "txt", "md", "docx"],
        help="支持PDF、TXT、MD、DOCX格式"
    )
    
    if uploaded_file and st.button("上传并处理"):
        with st.spinner("正在上传和处理文档..."):
            try:
                files = {"file": uploaded_file}
                response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
                
                if response.status_code == 200:
                    st.success(f"文档上传成功: {uploaded_file.name}")
                    st.rerun()
                else:
                    st.error(f"上传失败: {response.text}")
            except Exception as e:
                st.error(f"上传出错: {str(e)}")
    
    st.markdown("---")
    
    # 文档列表
    st.subheader("已上传文档")
    
    try:
        response = requests.get(f"{API_BASE_URL}/documents/")
        if response.status_code == 200:
            documents = response.json()
            
            if documents:
                selected_docs = []
                for doc in documents:
                    col_a, col_b = st.columns([4, 1])
                    with col_a:
                        checked = st.checkbox(
                            f"{doc['filename']} ({doc['chunk_count']}块)",
                            key=f"doc_{doc['id']}",
                            value=doc['id'] in st.session_state.selected_documents
                        )
                        if checked:
                            selected_docs.append(doc['id'])
                    with col_b:
                        if st.button("🗑️", key=f"del_{doc['id']}"):
                            try:
                                del_response = requests.delete(f"{API_BASE_URL}/documents/{doc['id']}")
                                if del_response.status_code == 200:
                                    st.success("删除成功")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"删除失败: {str(e)}")
                
                st.session_state.selected_documents = selected_docs
            else:
                st.info("暂无文档，请先上传")
        else:
            st.error("获取文档列表失败")
    except Exception as e:
        st.error(f"连接后端失败: {str(e)}")
        st.info("请确保后端服务已启动 (python backend/main.py)")
    
    st.markdown("---")
    
    # RAG配置
    st.header("⚙️ RAG配置")
    
    # RAG技术选择（改用checkbox）
    st.subheader("选择RAG技术")
    st.caption("可选择多个RAG技术进行对比")
    
    rag_techniques = {
        "simple_rag": "Simple RAG (基础)",
        "reranker_rag": "Reranker RAG (重排序)",
        "fusion_rag": "Fusion RAG (混合检索)",
        "hyde_rag": "HyDE RAG (假设文档)",
        "contextual_compression_rag": "Contextual Compression (上下文压缩)",
        "query_transformation_rag": "Query Transformation (查询转换)",
        "adaptive_rag": "Adaptive RAG (自适应)",
        "self_rag": "Self RAG (自我反思)",
        "crag": "CRAG (纠错)",
        "context_enriched_rag": "Context Enriched (上下文增强)",
        "contextual_chunk_headers_rag": "Chunk Headers (头部增强)",
        "hierarchical_rag": "Hierarchical Indices (层次化索引)",
        "doc_augmentation_rag": "Doc Augmentation (文档增强)",
        "semantic_chunking_rag": "Semantic Chunking (语义分块)",
        "rse_rag": "RSE (相关段落提取)",
        "chunk_size_selector_rag": "Chunk Size Selector (动态分块)",
        "proposition_chunking_rag": "Proposition Chunking (命题分块)",
        "graph_rag": "Graph RAG (知识图谱)",
    }
    
    # 使用checkbox形式
    selected_techniques = []
    
    # 基础检索增强（3个）
    st.markdown("**基础检索增强**")
    col1, col2 = st.columns(2)
    with col1:
        if st.checkbox(rag_techniques["simple_rag"], 
                      value="simple_rag" in st.session_state.selected_rag_techniques,
                      key="check_simple_rag"):
            selected_techniques.append("simple_rag")
        if st.checkbox(rag_techniques["fusion_rag"], 
                      value="fusion_rag" in st.session_state.selected_rag_techniques,
                      key="check_fusion_rag"):
            selected_techniques.append("fusion_rag")
    with col2:
        if st.checkbox(rag_techniques["reranker_rag"], 
                      value="reranker_rag" in st.session_state.selected_rag_techniques,
                      key="check_reranker_rag"):
            selected_techniques.append("reranker_rag")
        if st.checkbox(rag_techniques["hyde_rag"], 
                      value="hyde_rag" in st.session_state.selected_rag_techniques,
                      key="check_hyde_rag"):
            selected_techniques.append("hyde_rag")
    
    # 高级技术（5个）
    st.markdown("**高级技术**")
    col3, col4 = st.columns(2)
    with col3:
        if st.checkbox(rag_techniques["contextual_compression_rag"], 
                      value="contextual_compression_rag" in st.session_state.selected_rag_techniques,
                      key="check_contextual_compression_rag"):
            selected_techniques.append("contextual_compression_rag")
        if st.checkbox(rag_techniques["adaptive_rag"], 
                      value="adaptive_rag" in st.session_state.selected_rag_techniques,
                      key="check_adaptive_rag"):
            selected_techniques.append("adaptive_rag")
        if st.checkbox(rag_techniques["graph_rag"], 
                      value="graph_rag" in st.session_state.selected_rag_techniques,
                      key="check_graph_rag"):
            selected_techniques.append("graph_rag")
    with col4:
        if st.checkbox(rag_techniques["query_transformation_rag"], 
                      value="query_transformation_rag" in st.session_state.selected_rag_techniques,
                      key="check_query_transformation_rag"):
            selected_techniques.append("query_transformation_rag")
        if st.checkbox(rag_techniques["self_rag"], 
                      value="self_rag" in st.session_state.selected_rag_techniques,
                      key="check_self_rag"):
            selected_techniques.append("self_rag")
    
    # 纠错与增强（3个）- V1.4
    st.markdown("**纠错与增强** ✨")
    col5, col6 = st.columns(2)
    with col5:
        if st.checkbox(rag_techniques["crag"], 
                      value="crag" in st.session_state.selected_rag_techniques,
                      key="check_crag"):
            selected_techniques.append("crag")
        if st.checkbox(rag_techniques["context_enriched_rag"], 
                      value="context_enriched_rag" in st.session_state.selected_rag_techniques,
                      key="check_context_enriched_rag"):
            selected_techniques.append("context_enriched_rag")
    with col6:
        if st.checkbox(rag_techniques["contextual_chunk_headers_rag"], 
                      value="contextual_chunk_headers_rag" in st.session_state.selected_rag_techniques,
                      key="check_contextual_chunk_headers_rag"):
            selected_techniques.append("contextual_chunk_headers_rag")
    
    # 优化策略（3个）- V1.5
    st.markdown("**优化策略** 🚀")
    col7, col8 = st.columns(2)
    with col7:
        if st.checkbox(rag_techniques["hierarchical_rag"], 
                      value="hierarchical_rag" in st.session_state.selected_rag_techniques,
                      key="check_hierarchical_rag"):
            selected_techniques.append("hierarchical_rag")
        if st.checkbox(rag_techniques["semantic_chunking_rag"], 
                      value="semantic_chunking_rag" in st.session_state.selected_rag_techniques,
                      key="check_semantic_chunking_rag"):
            selected_techniques.append("semantic_chunking_rag")
    with col8:
        if st.checkbox(rag_techniques["doc_augmentation_rag"], 
                      value="doc_augmentation_rag" in st.session_state.selected_rag_techniques,
                      key="check_doc_augmentation_rag"):
            selected_techniques.append("doc_augmentation_rag")
    
    # 精细化策略（3个）- V1.6 NEW
    st.markdown("**精细化策略** 🎯")
    col9, col10 = st.columns(2)
    with col9:
        if st.checkbox(rag_techniques["rse_rag"], 
                      value="rse_rag" in st.session_state.selected_rag_techniques,
                      key="check_rse_rag"):
            selected_techniques.append("rse_rag")
        if st.checkbox(rag_techniques["proposition_chunking_rag"], 
                      value="proposition_chunking_rag" in st.session_state.selected_rag_techniques,
                      key="check_proposition_chunking_rag"):
            selected_techniques.append("proposition_chunking_rag")
    with col10:
        if st.checkbox(rag_techniques["chunk_size_selector_rag"], 
                      value="chunk_size_selector_rag" in st.session_state.selected_rag_techniques,
                      key="check_chunk_size_selector_rag"):
            selected_techniques.append("chunk_size_selector_rag")
    
    st.session_state.selected_rag_techniques = selected_techniques
    
    # 显示已选择数量
    if selected_techniques:
        st.success(f"✅ 已选择 {len(selected_techniques)} 个RAG技术")
    else:
        st.warning("⚠️ 请至少选择一个RAG技术")
    
    # 并发设置
    st.markdown("**⚡ 并发设置**")
    concurrent_num = st.slider(
        "查询并发数",
        min_value=1,
        max_value=10,
        value=3,
        help="同时执行多个RAG查询，提升速度。建议3-5"
    )
    st.session_state.concurrent_num = concurrent_num
    st.caption(f"💡 当前设置: 最多同时执行{concurrent_num}个RAG查询")
    
    # RAG参数
    with st.expander("RAG参数", expanded=False):
        top_k = st.slider("检索数量 (top_k)", 1, 20, 5)
        chunk_size = st.slider("分块大小", 100, 1000, 500, 50)
        chunk_overlap = st.slider("重叠大小", 0, 200, 100, 10)
        
        st.session_state.rag_config = {
            "top_k": top_k,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }
    
    # LLM配置
    with st.expander("LLM配置", expanded=False):
        temperature = st.slider("温度 (Temperature)", 0.0, 1.0, 0.7, 0.1)
        max_tokens = st.slider("最大Token数", 500, 4000, 2000, 100)
        
        st.session_state.llm_config = {
            "temperature": temperature,
            "max_tokens": max_tokens
        }
    
    # 自动评估配置
    with st.expander("🤖 自动评估配置", expanded=False):
        auto_eval_enabled = st.checkbox(
            "查询后自动评估",
            value=st.session_state.eval_config.get("auto_eval_enabled", False),
            help="完成查询后自动对所有RAG结果进行评估"
        )
        
        use_ragas = st.checkbox(
            "使用Ragas评估",
            value=st.session_state.eval_config.get("use_ragas", True),
            help="Ragas提供标准化的RAG评估指标（会增加评估时间）"
        )
        
        st.caption("📊 评估维度")
        st.caption("• LLM评分: 相关性、忠实度、连贯性、流畅度、简洁性")
        st.caption("• Ragas: Faithfulness、Answer Relevancy")
        
        # 更新session_state
        st.session_state.eval_config = {
            "auto_eval_enabled": auto_eval_enabled,
            "use_ragas": use_ragas
        }
        
        # 显示当前配置
        if use_ragas:
            st.info("✅ Ragas评估已启用（评估时间约5-8秒/RAG）")
        else:
            st.warning("⚠️ Ragas评估未启用（仅LLM评估，约2-3秒/RAG）")

