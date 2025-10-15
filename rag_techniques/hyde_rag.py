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
            self._log("hyde_prepare", "准备生成假设文档", {
                "query": query[:50] + "..." if len(query) > 50 else query,
                "query_length": len(query),
                "temperature": 0.7,
                "max_tokens": 500
            })
            
            prompt = self.hyde_prompt_template.format(query=query)
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            self._log("hyde_llm_call", "调用LLM生成假设文档")
            hypothesis = call_llm(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            self._log("hyde_generated", "假设文档生成完成", {
                "hypothesis_length": len(hypothesis),
                "hypothesis_preview": hypothesis[:150] + "..." if len(hypothesis) > 150 else hypothesis
            })
            
            logger.info(f"[HyDE RAG] 生成假设文档，长度: {len(hypothesis)} 字符")
            logger.debug(f"[HyDE RAG] 假设文档内容: {hypothesis[:200]}...")
            
            return hypothesis
            
        except Exception as e:
            self._log("hyde_generate_error", f"生成假设文档失败: {str(e)}", {"error": str(e)})
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
            self._log("hyde_search_start", f"使用假设文档进行向量检索，top_k={top_k}", {
                "hypothesis_length": len(hypothesis),
                "top_k": top_k
            })
            
            # 使用假设文档作为查询
            results = self.vector_store.similarity_search(
                query=hypothesis,
                top_k=top_k
            )
            
            self._log("hyde_search_complete", f"假设文档检索完成", {
                "result_count": len(results),
                "top_scores": [round(r["score"], 4) for r in results[:3]] if results else []
            })
            
            logger.info(f"[HyDE RAG] 使用假设文档检索到 {len(results)} 个文档")
            return results
            
        except Exception as e:
            self._log("hyde_search_error", f"检索失败: {str(e)}", {"error": str(e)})
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
                self._log("hyde_multi_hypothesis", "使用多假设文档模式（当前未实现完整融合）")
                search_results = self._search_with_hypothesis(hypothesis, top_k)
            
            if not search_results:
                self._log("hyde_no_results", "未找到相关文档")
                logger.warning("[HyDE RAG] 检索未找到文档")
                return []
            
            # Step 3: 转换为RetrievedDoc对象
            self._log("hyde_convert_docs", "转换检索结果为RetrievedDoc对象")
            retrieved_docs = []
            for idx, result in enumerate(search_results):
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
                
                # 记录前3个文档详情
                if idx < 3:
                    self._log(f"hyde_doc_{idx+1}", f"文档 #{idx+1}", {
                        "filename": result.get("filename", "Unknown"),
                        "score": round(result["score"], 4),
                        "content_length": len(result["content"]),
                        "content_preview": result["content"][:100] + "..."
                    })
            
            logger.info(f"[HyDE RAG] 检索完成，返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            self._log("retrieve_error", f"检索失败: {str(e)}", {"error": str(e)})
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
                self._log("generate_no_docs", "没有检索到文档，返回默认回答")
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 使用真实文档生成答案
            self._log("generate_prepare_context", "准备上下文（使用真实文档，非假设文档）", {
                "doc_count": len(retrieved_docs),
                "total_context_length": sum(len(doc.content) for doc in retrieved_docs),
                "using_original_query": True
            })
            
            context = [doc.content for doc in retrieved_docs]
            
            self._log("generate_llm_call", "调用LLM生成最终答案（使用原始查询）")
            answer = generate_rag_answer(
                query=query,  # 使用原始查询，不是假设文档
                context=context,
                system_prompt=self.system_prompt
            )
            
            self._log("generate_complete", "答案生成成功", {
                "answer_length": len(answer),
                "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer
            })
            
            logger.info(f"[HyDE RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            self._log("generate_error", f"生成答案失败: {str(e)}", {"error": str(e)})
            logger.error(f"[HyDE RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

