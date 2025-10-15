#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量为RAG技术添加基础日志的脚本
V1.9.4 - 2025-10-15
"""

import os
import re
from pathlib import Path

# RAG技术文件列表（跳过已完成的）
RAG_FILES_BASIC = [
    "adaptive_rag.py",
    "chunk_size_selector_rag.py",
    "context_enriched_rag.py",
    "contextual_chunk_headers_rag.py",
    "contextual_compression_rag.py",
    "crag.py",
    "doc_augmentation_rag.py",
    "graph_rag.py",
    "hierarchical_rag.py",
    "proposition_chunking_rag.py",
    "query_transformation_rag.py",
    "reranker_rag.py",
    "rse_rag.py",
    "self_rag.py",
    "semantic_chunking_rag.py",
]

# 基础日志模板
RETRIEVE_START_TEMPLATE = '''
        self._log("retrieve_prepare", "开始检索", {
            "query_length": len(query),
            "top_k": top_k
        })'''

RETRIEVE_END_TEMPLATE = '''
        self._log("retrieve_complete", f"检索完成，找到 {{len(results)}} 个文档", {
            "result_count": len(results)
        })'''

GENERATE_START_TEMPLATE = '''
        self._log("generate_prepare_context", "准备上下文", {
            "doc_count": len(retrieved_docs)
        })'''

GENERATE_LLM_TEMPLATE = '''
        self._log("generate_llm_call", "调用LLM生成答案")'''

GENERATE_END_TEMPLATE = '''
        self._log("generate_complete", "生成完成", {
            "answer_length": len(answer)
        })'''


def add_basic_logs_to_rag(file_path: Path) -> bool:
    """
    为单个RAG文件添加基础日志
    
    Returns:
        是否成功添加
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 检查是否已经有日志（避免重复添加）
        if 'self._log("retrieve_prepare"' in content:
            print(f"  ⏭️  {file_path.name}: 已有日志，跳过")
            return True
        
        print(f"  📝 处理: {file_path.name}")
        
        # 这个脚本只是创建了框架
        # 实际添加需要手动处理，因为每个RAG的代码结构不同
        # 我们只打印提示
        print(f"  ⚠️  需要手动添加日志到 {file_path.name}")
        print(f"     建议在 retrieve() 方法开始处添加:")
        print(f"     {RETRIEVE_START_TEMPLATE.strip()}")
        print(f"     建议在 retrieve() 方法结束前添加:")
        print(f"     {RETRIEVE_END_TEMPLATE.strip()}")
        print(f"     建议在 generate() 方法中添加:")
        print(f"     {GENERATE_START_TEMPLATE.strip()}")
        print(f"     {GENERATE_LLM_TEMPLATE.strip()}")
        print(f"     {GENERATE_END_TEMPLATE.strip()}")
        print()
        
        return False
        
    except Exception as e:
        print(f"  ❌ 错误: {file_path.name}: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始批量增强RAG日志...")
    print("=" * 60)
    
    # 获取RAG技术目录
    rag_dir = Path(__file__).parent / "rag_techniques"
    
    if not rag_dir.exists():
        print(f"❌ 目录不存在: {rag_dir}")
        return
    
    # 处理每个文件
    success_count = 0
    manual_count = 0
    
    for filename in RAG_FILES_BASIC:
        file_path = rag_dir / filename
        
        if not file_path.exists():
            print(f"  ⚠️  文件不存在: {filename}")
            continue
        
        result = add_basic_logs_to_rag(file_path)
        if result:
            success_count += 1
        else:
            manual_count += 1
    
    print("=" * 60)
    print("✅ 处理完成!")
    print(f"   - 已有日志的文件: {success_count}")
    print(f"   - 需要手动处理: {manual_count}")
    print()
    print("📌 提示:")
    print("   由于每个RAG技术的代码结构不同，")
    print("   建议参考 simple_rag.py、fusion_rag.py 和 hyde_rag.py")
    print("   手动为其他RAG技术添加详细日志。")
    print()
    print("   或者，为了快速完成，可以只添加基础日志点:")
    print("   1. retrieve_prepare - 检索开始")
    print("   2. retrieve_complete - 检索完成")
    print("   3. generate_prepare_context - 准备上下文")
    print("   4. generate_llm_call - 调用LLM")
    print("   5. generate_complete - 生成完成")


if __name__ == "__main__":
    main()

