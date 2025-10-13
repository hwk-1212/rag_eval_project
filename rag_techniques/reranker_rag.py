from typing import List, Dict, Any, Optional
from loguru import logger
import httpx
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer
from backend.config import settings


class RerankerRAG(BaseRAG):
    """Reranker RAG - 使用重排序模型优化检索结果
    
    流程：
    1. 向量检索获取更多候选文档（top_k * 2-3）
    2. 使用Reranker模型对候选文档重新打分
    3. 选择重排序后的top_k文档
    4. 将优化后的文档传递给LLM生成答案
    
    优势：
    - 显著提升检索准确性
    - 过滤不相关文档
    - 保留最相关的上下文
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Reranker RAG", vector_store, config)
        self.rerank_top_k = config.get("rerank_top_k", 20) if config else 20
        self.reranker_url = settings.RERANKER_BASE_URL
        self.reranker_api_key = settings.RERANKER_API_KEY
        self.reranker_model = settings.RERANKER_MODEL
        self.system_prompt = config.get("system_prompt") if config else None
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        使用重排序优化的检索
        
        Args:
            query: 查询文本
            top_k: 最终返回的文档数量
            
        Returns:
            重排序后的文档列表
        """
        try:
            # Step 1: 初始检索 - 获取更多候选文档
            candidate_count = min(self.rerank_top_k, top_k * 3)
            candidates = self.vector_store.similarity_search(
                query=query,
                top_k=candidate_count
            )
            
            if not candidates:
                logger.warning(f"[Reranker RAG] 初始检索未找到文档")
                return []
            
            logger.info(f"[Reranker RAG] 初始检索到 {len(candidates)} 个候选文档")
            
            # Step 2: 使用Reranker重新打分
            reranked = self._rerank_documents(query, candidates)
            
            # Step 3: 返回top_k
            final_docs = reranked[:top_k]
            
            # 转换为RetrievedDoc对象
            retrieved_docs = []
            for doc in final_docs:
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],
                    score=doc["rerank_score"],  # 使用重排序分数
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "original_score": doc.get("original_score", 0),
                        "rerank_score": doc.get("rerank_score", 0),
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            logger.info(f"[Reranker RAG] 重排序后返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Reranker RAG] 检索失败: {e}")
            return []
    
    def _rerank_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        使用Reranker模型对文档重新打分
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            重排序后的文档列表
        """
        try:
            # 准备文档内容列表
            doc_contents = [doc["content"] for doc in documents]
            
            # 调用Reranker API
            url = f"{self.reranker_url}/score/"
            headers = {
                "Authorization": f"Bearer {self.reranker_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.reranker_model,
                "text_1": query,
                "text_2": doc_contents
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                scores = result.get("scores", [])
                
                if not scores:
                    logger.warning("[Reranker RAG] Reranker返回空分数，使用原始分数")
                    return documents
                
                # 将重排序分数添加到文档中
                for i, doc in enumerate(documents):
                    doc["original_score"] = doc.get("score", 0)
                    doc["rerank_score"] = scores[i] if i < len(scores) else 0
                
                # 按重排序分数降序排序
                reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
                
                logger.info(f"[Reranker RAG] 重排序完成，分数范围: {min(scores):.4f} - {max(scores):.4f}")
                return reranked
                
        except Exception as e:
            logger.error(f"[Reranker RAG] 重排序失败: {e}")
            # 失败时返回原始文档
            return documents
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于重排序后的文档生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 重排序后的文档
            
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
            
            logger.info(f"[Reranker RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Reranker RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

