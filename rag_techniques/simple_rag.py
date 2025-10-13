from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer


class SimpleRAG(BaseRAG):
    """Simple RAG - 最基础的RAG实现
    
    流程：
    1. 对查询进行向量化
    2. 在向量库中检索相似文档
    3. 将检索结果作为上下文传递给LLM
    4. LLM生成最终答案
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Simple RAG", vector_store, config)
        self.system_prompt = config.get("system_prompt") if config else None
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            
        Returns:
            检索到的文档列表
        """
        try:
            # 使用向量存储进行相似度搜索
            search_results = self.vector_store.similarity_search(
                query=query,
                top_k=top_k
            )
            
            # 转换为RetrievedDoc对象
            retrieved_docs = []
            for result in search_results:
                doc = RetrievedDoc(
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    score=result["score"],
                    metadata={
                        "doc_id": result.get("doc_id", ""),
                        "filename": result.get("filename", ""),
                        "chunk_index": result.get("chunk_index", 0),
                    }
                )
                retrieved_docs.append(doc)
            
            logger.info(f"[Simple RAG] 检索到 {len(retrieved_docs)} 个相关文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Simple RAG] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于检索结果生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 检索到的文档
            
        Returns:
            生成的答案
        """
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 提取文档内容
            context = [doc.content for doc in retrieved_docs]
            
            # 调用LLM生成答案
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[Simple RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Simple RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

