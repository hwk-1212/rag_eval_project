"""
主页面 - Page 1
包含：配置区、对话窗口、知识库管理
"""
import streamlit as st
import requests
from datetime import datetime
import os

API_BASE_URL = "http://localhost:8000/api/v1"


def render_main_page():
    """
    主页面布局：
    ┌────────────────────────────────┐
    │ 配置区（LLM、RAG、评估）        │
    ├─────────────────┬──────────────┤
    │ 对话区域         │  知识库      │
    │                 │              │
    └─────────────────┴──────────────┘
    """
    
    # ========== 顶部配置区 ==========
    with st.expander("⚙️ 配置区", expanded=True):
        config_col1, config_col2, config_col3 = st.columns(3)
        
        # LLM配置（包含API密钥和模型）
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
    
    # ========== 底部：对话区 + 知识库 ==========
    chat_col, kb_col = st.columns([7, 3])
    
    with chat_col:
        st.markdown("### 💬 对话区域")
        render_chat_window()
    
    with kb_col:
        st.markdown("### 📚 知识库")
        render_knowledge_base_section()


def render_llm_config():
    """LLM配置区（包含API密钥、模型、参数）"""
    # 初始化LLM配置
    if "llm_config" not in st.session_state:
        # 从环境变量读取默认值
        default_api_key = os.getenv("LLM_API_KEY", "sk-e96412163b6a4f6189b65b98532eaf77")
        default_model = os.getenv("LLM_MODEL_ID", "qwen-plus")
        
        st.session_state.llm_config = {
            "api_key": default_api_key,
            "model": default_model,
            "temperature": 0.7,
            "max_tokens": 2000
        }
    
    llm_config = st.session_state.llm_config
    
    # API密钥
    api_key = st.text_input(
        "🔑 百炼API密钥",
        value=llm_config.get("api_key", ""),
        type="password",
        key="llm_api_key",
        help="从环境变量或手动输入"
    )
    llm_config["api_key"] = api_key
    
    # 模型选择
    model_options = ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long", "gpt-4", "gpt-3.5-turbo"]
    current_model = llm_config.get("model", "qwen-plus")
    model_index = model_options.index(current_model) if current_model in model_options else 0
    
    selected_model = st.selectbox(
        "🎯 模型选择",
        options=model_options,
        index=model_index,
        key="llm_model_select"
    )
    llm_config["model"] = selected_model
    
    # Temperature
    llm_config["temperature"] = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=llm_config.get("temperature", 0.7),
        step=0.1,
        key="llm_temp"
    )
    
    # Max Tokens
    llm_config["max_tokens"] = st.number_input(
        "Max Tokens",
        min_value=100,
        max_value=4000,
        value=llm_config.get("max_tokens", 2000),
        step=100,
        key="llm_tokens"
    )


def render_rag_selection():
    """RAG技术选择区（checkbox勾选）"""
    if "selected_rag_techniques" not in st.session_state:
        st.session_state.selected_rag_techniques = ["simple_rag"]
    
    rag_techniques = {
        "simple_rag": "Simple RAG",
        "reranker_rag": "Reranker RAG",
        "fusion_rag": "Fusion RAG",
        "hyde_rag": "HyDE RAG",
        "contextual_compression_rag": "Contextual Compression",
        "query_transformation_rag": "Query Transformation",
        "adaptive_rag": "Adaptive RAG",
        "self_rag": "Self RAG",
        "crag": "CRAG",
        "context_enriched_rag": "Context Enriched",
        "contextual_chunk_headers_rag": "Contextual Chunk Headers",
        "hierarchical_rag": "Hierarchical RAG",
        "doc_augmentation_rag": "Doc Augmentation",
        "semantic_chunking_rag": "Semantic Chunking",
        "rse_rag": "RSE RAG",
        "chunk_size_selector_rag": "Chunk Size Selector",
        "proposition_chunking_rag": "Proposition Chunking",
        "graph_rag": "Graph RAG",
    }
    
    # 使用checkbox形式（紧凑排列）
    selected_techniques = []
    
    # 分组显示（每行2个）
    rag_items = list(rag_techniques.items())
    for i in range(0, len(rag_items), 2):
        col1, col2 = st.columns(2)
        
        # 第一个checkbox
        with col1:
            key1, name1 = rag_items[i]
            if st.checkbox(
                name1, 
                value=key1 in st.session_state.selected_rag_techniques,
                key=f"rag_check_{key1}"
            ):
                selected_techniques.append(key1)
        
        # 第二个checkbox（如果存在）
        with col2:
            if i + 1 < len(rag_items):
                key2, name2 = rag_items[i + 1]
                if st.checkbox(
                    name2, 
                    value=key2 in st.session_state.selected_rag_techniques,
                    key=f"rag_check_{key2}"
                ):
                    selected_techniques.append(key2)
    
    # 更新选中的技术
    st.session_state.selected_rag_techniques = selected_techniques if selected_techniques else ["simple_rag"]
    
    st.markdown("---")
    
    # 并发设置
    concurrent_num = st.slider(
        "⚡ 查询并发数",
        min_value=1,
        max_value=10,
        value=st.session_state.get("concurrent_num", 3),
        key="main_concurrent",
        help="同时执行多个RAG查询，提升速度"
    )
    st.session_state.concurrent_num = concurrent_num
    
    st.caption(f"✅ 已选择 {len(st.session_state.selected_rag_techniques)} 个RAG技术")


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
        st.caption(f"📝 当前会话: {st.session_state.current_session_id}")
    
    # 显示历史消息
    chat_container = st.container(height=500)
    
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 欢迎使用RAG评测对比平台！请在下方输入您的问题。")
        else:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if "timestamp" in message:
                        st.caption(message["timestamp"])
    
    # 底部按钮
    btn_col1, btn_col2 = st.columns([1, 1])
    
    with btn_col1:
        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.rag_results = []
            st.rerun()
    
    with btn_col2:
        if st.button("📊 查看RAG对比", use_container_width=True, type="primary"):
            st.info("💡 请切换到「RAG对比」标签页查看详细对比")
    
    # 输入框
    query = st.chat_input("💬 请输入您的问题...")
    
    if query:
        handle_query(query)


def render_knowledge_base_section():
    """知识库管理区域（右侧）"""
    # 文档上传
    uploaded_file = st.file_uploader(
        "📤 上传文档",
        type=["pdf", "txt", "md", "docx"],
        help="支持PDF、TXT、MD、DOCX格式",
        key="kb_uploader"
    )
    
    if uploaded_file and st.button("上传并处理", use_container_width=True, key="kb_upload_btn"):
        with st.spinner("正在上传和处理文档..."):
            try:
                files = {"file": uploaded_file}
                response = requests.post(f"{API_BASE_URL}/documents/upload", files=files)
                
                if response.status_code == 200:
                    st.success(f"✅ 文档上传成功")
                    st.rerun()
                else:
                    st.error(f"❌ 上传失败: {response.text}")
            except Exception as e:
                st.error(f"❌ 上传出错: {str(e)}")
    
    st.markdown("---")
    
    # 文档列表
    st.subheader("📚 文档列表")
    
    try:
        response = requests.get(f"{API_BASE_URL}/documents/")
        if response.status_code == 200:
            documents = response.json()
            
            if documents:
                if "selected_documents" not in st.session_state:
                    st.session_state.selected_documents = []
                
                # 显示文档列表（带选择和删除）
                for doc in documents:
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        is_selected = doc["id"] in st.session_state.selected_documents
                        if st.checkbox(
                            f"📄 {doc['filename']}",
                            value=is_selected,
                            key=f"kb_doc_{doc['id']}"
                        ):
                            if doc["id"] not in st.session_state.selected_documents:
                                st.session_state.selected_documents.append(doc["id"])
                        else:
                            if doc["id"] in st.session_state.selected_documents:
                                st.session_state.selected_documents.remove(doc["id"])
                    
                    with col2:
                        if st.button("🗑️", key=f"kb_del_{doc['id']}", help="删除文档"):
                            try:
                                del_response = requests.delete(f"{API_BASE_URL}/documents/{doc['id']}")
                                if del_response.status_code == 200:
                                    st.success("删除成功")
                                    st.rerun()
                                else:
                                    st.error(f"删除失败")
                            except Exception as e:
                                st.error(f"删除出错: {str(e)}")
                
                st.caption(f"✅ 已选择 {len(st.session_state.selected_documents)} 个文档")
            else:
                st.info("📭 暂无文档，请上传")
        else:
            st.error("❌ 获取文档列表失败")
    except Exception as e:
        st.error(f"❌ 加载失败: {str(e)}")


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

