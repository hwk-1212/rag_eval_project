from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import call_llm, generate_rag_answer
from backend.utils.embedding import get_single_embedding
import numpy as np


class HyDERAG(BaseRAG):
    """HyDE RAG - 假设文档嵌入 (Hypothetical Document Embeddings)
    
    流程：
    1. 使用LLM根据查询生成假设答案（假设文档）
    2. 将假设文档向量化
    3. 使用假设文档向量进行检索
    4. 获取真实的相关文档
    5. 基于真实文档生成最终答案
    
    优势：
    - 改善查询-文档语义匹配
    - 处理抽象或复杂查询
    - 提高检索召回率
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("HyDE RAG", vector_store, config)
        self.num_hypotheses = config.get("num_hypotheses", 1) if config else 1
        self.system_prompt = config.get("system_prompt") if config else None
        self.hyde_prompt_template = """请根据以下问题生成一个假设的详细答案。
这个答案应该包含可能的相关信息和术语，用于帮助检索真实文档。

问题：{query}

请生成假设答案："""
    
    def _generate_hypothetical_document(self, query: str) -> str:
        """
        生成假设文档
        
        Args:
            query: 用户查询
            
        Returns:
            假设文档内容
        """
        try:
            prompt = self.hyde_prompt_template.format(query=query)
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            hypothesis = call_llm(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            logger.info(f"[HyDE RAG] 生成假设文档，长度: {len(hypothesis)} 字符")
            logger.debug(f"[HyDE RAG] 假设文档内容: {hypothesis[:200]}...")
            
            return hypothesis
            
        except Exception as e:
            logger.error(f"[HyDE RAG] 生成假设文档失败: {e}")
            # 失败时返回原始查询
            return query
    
    def _search_with_hypothesis(
        self,
        hypothesis: str,
        top_k: int
    ) -> List[Dict]:
        """
        使用假设文档进行检索
        
        Args:
            hypothesis: 假设文档
            top_k: 返回文档数
            
        Returns:
            检索结果
        """
        try:
            # 使用假设文档作为查询
            results = self.vector_store.similarity_search(
                query=hypothesis,
                top_k=top_k
            )
            
            logger.info(f"[HyDE RAG] 使用假设文档检索到 {len(results)} 个文档")
            return results
            
        except Exception as e:
            logger.error(f"[HyDE RAG] 检索失败: {e}")
            return []
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        HyDE检索流程
        
        Args:
            query: 用户查询
            top_k: 返回文档数
            
        Returns:
            检索到的文档列表
        """
        try:
            # Step 1: 生成假设文档
            hypothesis = self._generate_hypothetical_document(query)
            
            # Step 2: 使用假设文档检索
            if self.num_hypotheses == 1:
                # 单个假设文档
                search_results = self._search_with_hypothesis(hypothesis, top_k)
            else:
                # 多个假设文档（可选功能）
                # TODO: 实现多假设文档融合
                search_results = self._search_with_hypothesis(hypothesis, top_k)
            
            if not search_results:
                logger.warning("[HyDE RAG] 检索未找到文档")
                return []
            
            # Step 3: 转换为RetrievedDoc对象
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
                        "hypothesis_used": hypothesis[:200],  # 记录使用的假设文档
                    }
                )
                retrieved_docs.append(doc)
            
            logger.info(f"[HyDE RAG] 检索完成，返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[HyDE RAG] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于检索到的真实文档生成答案
        
        Args:
            query: 原始查询
            retrieved_docs: 检索到的真实文档
            
        Returns:
            生成的答案
        """
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 使用真实文档生成答案
            context = [doc.content for doc in retrieved_docs]
            
            answer = generate_rag_answer(
                query=query,  # 使用原始查询，不是假设文档
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[HyDE RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[HyDE RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

