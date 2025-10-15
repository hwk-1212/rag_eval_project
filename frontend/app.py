import streamlit as st
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from frontend.pages.main_page import render_main_page
from frontend.pages.comparison_page import render_comparison_page
from frontend.pages.statistics_page import render_statistics_page

# 页面配置
st.set_page_config(
    page_title="RAG评测对比平台",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 自定义CSS
st.markdown("""
<style>
    .main {
        padding: 0.5rem;
    }
    .stButton>button {
        width: 100%;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 0.5rem;
        font-size: 2rem;
    }
    h2 {
        font-size: 1.5rem;
        padding-top: 0.5rem;
    }
    h3 {
        font-size: 1.2rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background-color: #f0f2f6;
        padding: 0.5rem;
        border-radius: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    /* 紧凑的卡片样式 */
    .element-container {
        margin-bottom: 0.5rem;
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
if "current_page" not in st.session_state:
    st.session_state.current_page = "主页面"

# 主标题
st.title("🤖 RAG评测对比平台 v1.7")

# 顶部页面切换
page_tabs = st.tabs(["🏠 主页面", "📊 RAG对比", "📈 统计分析"])

# Page 1: 主页面
with page_tabs[0]:
    render_main_page()

# Page 2: RAG对比
with page_tabs[1]:
    render_comparison_page()

# Page 3: 统计分析
with page_tabs[2]:
    render_statistics_page()

# 页脚
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; padding: 0.5rem;'>
        RAG评测对比平台 v1.7 | 已实现18/19 RAG技术 | Powered by FastAPI & Streamlit
    </div>
    """,
    unsafe_allow_html=True
)

