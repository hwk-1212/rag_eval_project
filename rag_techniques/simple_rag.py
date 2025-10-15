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
            # 记录检索开始
            self._log("retrieve_prepare", "准备进行向量检索", {
                "query_preview": query[:50] + "..." if len(query) > 50 else query,
                "query_length": len(query),
                "top_k": top_k
            })
            
            # 使用向量存储进行相似度搜索
            search_results = self.vector_store.similarity_search(
                query=query,
                top_k=top_k
            )
            
            self._log("retrieve_search_complete", f"向量搜索完成，返回 {len(search_results)} 个结果", {
                "result_count": len(search_results),
                "top_scores": [round(r["score"], 4) for r in search_results[:3]] if search_results else []
            })
            
            # 转换为RetrievedDoc对象
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
                    }
                )
                retrieved_docs.append(doc)
                
                # 记录每个文档的详细信息
                if idx < 3:  # 只记录前3个
                    self._log(f"retrieve_doc_{idx+1}", f"文档 #{idx+1}: {result.get('filename', 'Unknown')}", {
                        "chunk_id": result["chunk_id"],
                        "score": round(result["score"], 4),
                        "content_length": len(result["content"]),
                        "content_preview": result["content"][:100] + "..." if len(result["content"]) > 100 else result["content"]
                    })
            
            logger.info(f"[Simple RAG] 检索到 {len(retrieved_docs)} 个相关文档")
            return retrieved_docs
            
        except Exception as e:
            self._log("retrieve_error", f"检索失败: {str(e)}", {"error": str(e)})
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
                self._log("generate_no_docs", "没有检索到文档，返回默认回答")
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 提取文档内容
            self._log("generate_prepare_context", "准备上下文信息", {
                "doc_count": len(retrieved_docs),
                "total_context_length": sum(len(doc.content) for doc in retrieved_docs),
                "avg_doc_length": round(sum(len(doc.content) for doc in retrieved_docs) / len(retrieved_docs), 2)
            })
            
            context = [doc.content for doc in retrieved_docs]
            
            # 调用LLM生成答案
            self._log("generate_llm_call", "调用LLM生成答案", {
                "context_count": len(context),
                "has_system_prompt": self.system_prompt is not None
            })
            
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            self._log("generate_complete", "答案生成成功", {
                "answer_length": len(answer),
                "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer
            })
            
            logger.info(f"[Simple RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            self._log("generate_error", f"生成答案失败: {str(e)}", {"error": str(e)})
            logger.error(f"[Simple RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

