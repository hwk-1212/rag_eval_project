import streamlit as st
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from frontend.components.sidebar import render_sidebar
from frontend.components.main_chat import render_main_chat
from frontend.components.rag_comparison import render_rag_comparison

# 页面配置
st.set_page_config(
    page_title="RAG评测对比平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 0rem;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 初始化session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "selected_documents" not in st.session_state:
    st.session_state.selected_documents = []
if "selected_rag_techniques" not in st.session_state:
    st.session_state.selected_rag_techniques = ["simple_rag"]
if "rag_results" not in st.session_state:
    st.session_state.rag_results = []

# 主标题
st.title("🤖 RAG评测对比平台")

# 创建三栏布局
col1, col2, col3 = st.columns([2.5, 4, 3.5])

# 左侧栏 - 文件管理和配置
with col1:
    render_sidebar()

# 中间栏 - 主对话窗口
with col2:
    render_main_chat()

# 右侧栏 - RAG结果对比
with col3:
    render_rag_comparison()

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 1rem;'>
        RAG评测对比平台 v1.0.0 | Powered by FastAPI & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)

