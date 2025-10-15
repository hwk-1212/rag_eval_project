"""
主页面 - Page 1
包含：配置区、对话窗口、知识库管理
"""
import streamlit as st
import requests
from datetime import datetime
from frontend.components.sidebar import render_config_section, render_knowledge_base_section

API_BASE_URL = "http://localhost:8000/api/v1"


def render_main_page():
    """
    主页面布局：
    - 顶部：配置区（LLM、RAG、评估）
    - 中间：对话窗口
    - 底部：知识库选择和文档管理
    """
    
    # ========== 顶部配置区 ==========
    with st.expander("⚙️ 配置区", expanded=False):
        config_col1, config_col2, config_col3 = st.columns(3)
        
        # LLM配置
        with config_col1:
            st.markdown("### 🤖 LLM配置")
            render_llm_config()
        
        # RAG技术选择
        with config_col2:
            st.markdown("### 🔧 RAG技术选择")
            render_rag_selection()
        
        # 评估配置
        with config_col3:
            st.markdown("### 📊 评估配置")
            render_eval_config()
    
    st.markdown("---")
    
    # ========== 中间对话窗口 ==========
    st.markdown("### 💬 对话窗口")
    
    render_chat_window()
    
    st.markdown("---")
    
    # ========== 底部知识库管理 ==========
    st.markdown("### 📚 知识库管理")
    
    kb_col1, kb_col2 = st.columns([3, 7])
    
    with kb_col1:
        # 百炼API配置
        with st.expander("🔑 API密钥配置", expanded=False):
            api_key = st.text_input(
                "百炼API密钥",
                value=st.session_state.get("api_key", ""),
                type="password",
                key="main_api_key"
            )
            if api_key != st.session_state.get("api_key"):
                st.session_state.api_key = api_key
                st.success("API密钥已更新")
        
        # 模型选择
        with st.expander("🎯 模型选择", expanded=False):
            model_options = ["qwen-plus", "qwen-turbo", "qwen-max", "gpt-4", "gpt-3.5-turbo"]
            selected_model = st.selectbox(
                "选择LLM模型",
                options=model_options,
                index=0,
                key="main_model_select"
            )
            st.session_state.selected_model = selected_model
    
    with kb_col2:
        # 知识库选择和文档管理
        render_knowledge_base_section()


def render_llm_config():
    """LLM配置区"""
    # 初始化LLM配置
    if "llm_config" not in st.session_state:
        st.session_state.llm_config = {
            "model": "qwen-plus",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    
    llm_config = st.session_state.llm_config
    
    llm_config["temperature"] = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=llm_config.get("temperature", 0.7),
        step=0.1,
        key="llm_temp"
    )
    
    llm_config["max_tokens"] = st.number_input(
        "Max Tokens",
        min_value=100,
        max_value=4000,
        value=llm_config.get("max_tokens", 2000),
        step=100,
        key="llm_tokens"
    )
    
    st.caption(f"模型: {llm_config.get('model', 'qwen-plus')}")


def render_rag_selection():
    """RAG技术选择区（紧凑版）"""
    if "selected_rag_techniques" not in st.session_state:
        st.session_state.selected_rag_techniques = ["simple_rag"]
    
    rag_techniques = {
        "simple_rag": "Simple RAG",
        "reranker_rag": "Reranker RAG",
        "fusion_rag": "Fusion RAG",
        "hyde_rag": "HyDE RAG",
        "contextual_compression_rag": "Compression",
        "query_transformation_rag": "Query Transform",
        "adaptive_rag": "Adaptive RAG",
        "self_rag": "Self RAG",
        "crag": "CRAG",
        "context_enriched_rag": "Context Enriched",
        "contextual_chunk_headers_rag": "Chunk Headers",
        "hierarchical_rag": "Hierarchical",
        "doc_augmentation_rag": "Doc Augmentation",
        "semantic_chunking_rag": "Semantic Chunking",
        "rse_rag": "RSE",
        "chunk_size_selector_rag": "Chunk Size Selector",
        "proposition_chunking_rag": "Proposition",
        "graph_rag": "Graph RAG",
    }
    
    # 多选框（紧凑显示）
    selected = st.multiselect(
        "选择RAG技术",
        options=list(rag_techniques.keys()),
        default=st.session_state.selected_rag_techniques,
        format_func=lambda x: rag_techniques[x],
        key="rag_multiselect"
    )
    
    st.session_state.selected_rag_techniques = selected if selected else ["simple_rag"]
    
    # 并发设置
    concurrent_num = st.slider(
        "并发数",
        min_value=1,
        max_value=10,
        value=st.session_state.get("concurrent_num", 3),
        key="main_concurrent"
    )
    st.session_state.concurrent_num = concurrent_num
    
    st.caption(f"已选择 {len(st.session_state.selected_rag_techniques)} 个技术")


def render_eval_config():
    """评估配置区"""
    if "eval_config" not in st.session_state:
        st.session_state.eval_config = {
            "auto_eval_enabled": False,
            "use_ragas": False
        }
    
    eval_config = st.session_state.eval_config
    
    eval_config["auto_eval_enabled"] = st.checkbox(
        "查询后自动评估",
        value=eval_config.get("auto_eval_enabled", False),
        key="auto_eval_check"
    )
    
    eval_config["use_ragas"] = st.checkbox(
        "使用Ragas评估",
        value=eval_config.get("use_ragas", False),
        key="ragas_check"
    )
    
    if eval_config["auto_eval_enabled"]:
        st.success("✅ 自动评估已启用")
    else:
        st.info("⏸️ 手动评估模式")


def render_chat_window():
    """对话窗口"""
    # 会话信息
    if st.session_state.current_session_id:
        st.caption(f"📝 会话ID: {st.session_state.current_session_id}")
    
    # 显示历史消息
    chat_container = st.container(height=400)
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "timestamp" in message:
                    st.caption(message["timestamp"])
    
    # 底部按钮和输入
    btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 6])
    
    with btn_col1:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.rag_results = []
            st.rerun()
    
    with btn_col2:
        if st.button("📊 查看对比", use_container_width=True, type="primary"):
            st.info("💡 请切换到「RAG对比」页面查看详细对比")
    
    with btn_col3:
        st.caption("💬 在下方输入框提问")
    
    # 输入框
    query = st.chat_input("请输入您的问题...")
    
    if query:
        handle_query(query)


def handle_query(query: str):
    """处理用户查询"""
    # 验证
    if not st.session_state.selected_documents:
        st.error("❌ 请先选择至少一个文档")
        return
    
    if not st.session_state.selected_rag_techniques:
        st.error("❌ 请先选择至少一个RAG技术")
        return
    
    # 添加用户消息
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.messages.append({
        "role": "user",
        "content": query,
        "timestamp": timestamp
    })
    
    # 调用后端API
    with st.spinner("🤔 正在思考..."):
        try:
            rag_config = st.session_state.get("rag_config", {})
            rag_config["concurrent_num"] = st.session_state.get("concurrent_num", 3)
            
            payload = {
                "query": query,
                "document_ids": st.session_state.selected_documents,
                "rag_techniques": st.session_state.selected_rag_techniques,
                "session_id": st.session_state.current_session_id,
                "llm_config": st.session_state.get("llm_config", {}),
                "rag_config": rag_config
            }
            
            response = requests.post(
                f"{API_BASE_URL}/qa/query",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 保存会话ID和结果
                st.session_state.current_session_id = result["session_id"]
                st.session_state.rag_results = result["results"]
                
                # 显示主要回答
                if result["results"]:
                    main_answer = result["results"][0]["answer"]
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": main_answer,
                        "timestamp": timestamp
                    })
                    
                    st.success(f"✅ 已使用 {len(result['results'])} 种RAG技术完成回答")
                    
                    # 如果启用自动评估
                    if st.session_state.eval_config.get("auto_eval_enabled"):
                        st.info("🤖 正在进行自动评估...")
                    
                    st.rerun()
                else:
                    st.error("❌ 未获取到任何结果")
            else:
                st.error(f"❌ 查询失败: {response.text}")
                
        except requests.exceptions.Timeout:
            st.error("⏱️ 请求超时，请稍后重试")
        except Exception as e:
            st.error(f"❌ 查询出错: {str(e)}")

