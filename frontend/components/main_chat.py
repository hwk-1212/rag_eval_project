import streamlit as st
import requests
from datetime import datetime

API_BASE_URL = "http://localhost:8000/api/v1"


def render_main_chat():
    """渲染中间主对话窗口"""
    
    st.header("💬 对话窗口")
    
    # 会话信息
    if st.session_state.current_session_id:
        st.caption(f"当前会话 ID: {st.session_state.current_session_id}")
    
    # 显示历史消息
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if "timestamp" in message:
                    st.caption(message["timestamp"])
    
    # 输入框
    query = st.chat_input("请输入您的问题...")
    
    if query:
        # 验证是否选择了文档
        if not st.session_state.selected_documents:
            st.error("请先选择至少一个文档")
            return
        
        # 验证是否选择了RAG技术
        if not st.session_state.selected_rag_techniques:
            st.error("请先选择至少一个RAG技术")
            return
        
        # 添加用户消息
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state.messages.append({
            "role": "user",
            "content": query,
            "timestamp": timestamp
        })
        
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(query)
            st.caption(timestamp)
        
        # 调用后端API
        with st.chat_message("assistant"):
            with st.spinner("正在思考..."):
                try:
                    # 准备请求
                    payload = {
                        "query": query,
                        "document_ids": st.session_state.selected_documents,
                        "rag_techniques": st.session_state.selected_rag_techniques,
                        "session_id": st.session_state.current_session_id,
                        "llm_config": st.session_state.get("llm_config", {}),
                        "rag_config": st.session_state.get("rag_config", {})
                    }
                    
                    response = requests.post(
                        f"{API_BASE_URL}/qa/query",
                        json=payload,
                        timeout=120
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 保存会话ID
                        st.session_state.current_session_id = result["session_id"]
                        
                        # 保存RAG结果
                        st.session_state.rag_results = result["results"]
                        
                        # 显示主要回答（第一个RAG技术的结果）
                        if result["results"]:
                            main_answer = result["results"][0]["answer"]
                            st.markdown(main_answer)
                            st.caption(f"{timestamp} | {result['results'][0]['rag_technique']}")
                            
                            # 添加助手消息
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": main_answer,
                                "timestamp": timestamp
                            })
                            
                            # 如果有多个RAG技术，显示提示
                            if len(result["results"]) > 1:
                                st.info(f"✨ 已使用 {len(result['results'])} 种RAG技术，详细对比请查看右侧面板")
                        else:
                            st.error("未获取到任何结果")
                    else:
                        st.error(f"查询失败: {response.text}")
                        
                except requests.exceptions.Timeout:
                    st.error("请求超时，请稍后重试")
                except Exception as e:
                    st.error(f"查询出错: {str(e)}")
    
    # 清空对话按钮
    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.session_state.rag_results = []
        st.rerun()

