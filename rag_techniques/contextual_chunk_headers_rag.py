from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer, call_llm


class ContextualChunkHeadersRAG(BaseRAG):
    """Contextual Chunk Headers RAG - 上下文chunk头部RAG
    
    流程：
    1. 向量检索获取相关文档chunks
    2. 为每个chunk生成描述性的header/标题
    3. 将header和chunk内容组合
    4. 基于带header的增强chunks生成答案
    
    Header内容：
    - 文档标题
    - chunk主题摘要
    - 关键信息概括
    
    优势：
    - 帮助LLM理解chunk的上下文和来源
    - 提供chunk的高层次概览
    - 改善信息的可理解性
    - 特别适合长文档和跨文档检索
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Contextual Chunk Headers RAG", vector_store, config)
        self.system_prompt = config.get("system_prompt") if config else None
        self.include_filename = config.get("include_filename", True) if config else True
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        使用chunk headers策略检索文档
        
        Args:
            query: 查询文本
            top_k: 返回文档数量
            
        Returns:
            带有headers的文档列表
        """
        try:
            # Step 1: 初始检索
            docs = self.vector_store.similarity_search(
                query=query,
                top_k=top_k
            )
            
            if not docs:
                logger.warning(f"[Contextual Chunk Headers RAG] 未找到文档")
                return []
            
            logger.info(f"[Contextual Chunk Headers RAG] 检索到 {len(docs)} 个文档")
            
            # Step 2: 为每个chunk生成header
            docs_with_headers = []
            
            for doc in docs:
                # 生成header
                header = self._generate_chunk_header(
                    chunk_content=doc["content"],
                    filename=doc.get("filename", ""),
                    chunk_index=doc.get("chunk_index", 0)
                )
                
                # 组合header和content
                enriched_content = f"{header}\n\n{doc['content']}"
                
                doc_with_header = {
                    "chunk_id": doc["chunk_id"],
                    "content": enriched_content,
                    "score": doc["score"],
                    "doc_id": doc.get("doc_id", ""),
                    "filename": doc.get("filename", ""),
                    "chunk_index": doc.get("chunk_index", 0),
                    "header": header,
                    "original_content": doc["content"]
                }
                docs_with_headers.append(doc_with_header)
            
            # 转换为RetrievedDoc对象
            retrieved_docs = []
            for doc in docs_with_headers:
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],  # 包含header的内容
                    score=doc["score"],
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "header": doc.get("header", ""),
                        "has_header": True,
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            logger.info(f"[Contextual Chunk Headers RAG] 返回 {len(retrieved_docs)} 个带header的文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Contextual Chunk Headers RAG] 检索失败: {e}")
            return []
    
    def _generate_chunk_header(
        self,
        chunk_content: str,
        filename: str = "",
        chunk_index: int = 0
    ) -> str:
        """
        为chunk生成描述性header
        
        Args:
            chunk_content: chunk内容
            filename: 文件名
            chunk_index: chunk索引
            
        Returns:
            生成的header
        """
        try:
            # 构建header的基本信息
            header_parts = []
            
            if self.include_filename and filename:
                header_parts.append(f"【文档: {filename}】")
            
            if chunk_index is not None:
                header_parts.append(f"【片段 #{chunk_index + 1}】")
            
            # 使用LLM生成chunk的主题摘要
            system_prompt = """为给定的文本片段生成一个简洁的主题标题。
要求：
- 10-20字以内
- 概括主要内容
- 突出关键信息
- 不要使用"本文"、"该段"等指代词

只返回标题，不要有其他内容。"""
            
            # 限制chunk长度以减少token消耗
            truncated_content = chunk_content[:300] if len(chunk_content) > 300 else chunk_content
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请为以下文本生成主题标题:\n\n{truncated_content}"}
            ]
            
            topic_title = call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=50
            ).strip()
            
            # 组合完整的header
            if topic_title:
                header_parts.append(f"【主题: {topic_title}】")
            
            header = " ".join(header_parts)
            
            logger.debug(f"[Contextual Chunk Headers RAG] 生成header: {header}")
            return header
            
        except Exception as e:
            logger.error(f"[Contextual Chunk Headers RAG] 生成header失败: {e}")
            # 返回基本header
            basic_header = f"【文档: {filename}】【片段 #{chunk_index + 1}】" if filename else f"【片段 #{chunk_index + 1}】"
            return basic_header
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于带header的chunks生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 带header的文档
            
        Returns:
            生成的答案
        """
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 提取文档内容（已包含headers）
            context = [doc.content for doc in retrieved_docs]
            
            # 调用LLM生成答案
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[Contextual Chunk Headers RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Contextual Chunk Headers RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

