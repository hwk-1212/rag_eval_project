"""
Pages package for RAG evaluation platform
"""
from .main_page import render_main_page
from .comparison_page import render_comparison_page
from .statistics_page import render_statistics_page

__all__ = [
    "render_main_page",
    "render_comparison_page",
    "render_statistics_page"
]

