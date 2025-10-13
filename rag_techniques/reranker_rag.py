from typing import List, Dict, Any, Optional
from loguru import logger
import re
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer, call_llm
from backend.config import settings


class RerankerRAG(BaseRAG):
    """Reranker RAG - 使用LLM重排序优化检索结果
    
    流程：
    1. 向量检索获取更多候选文档（top_k * 2-3）
    2. 使用LLM对候选文档进行相关性评分（0-10分）
    3. 按评分降序排序，选择top_k文档
    4. 将优化后的文档传递给LLM生成答案
    
    重排序方法：
    - llm: 使用LLM对每个文档评分（准确但较慢）
    - keywords: 基于关键词匹配打分（快速但较简单）
    
    优势：
    - 显著提升检索准确性，过滤不相关文档
    - LLM评分考虑语义相关性，优于向量相似度
    - 支持多种重排序策略
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Reranker RAG", vector_store, config)
        self.rerank_top_k = config.get("rerank_top_k", 20) if config else 20
        self.system_prompt = config.get("system_prompt") if config else None
        self.rerank_method = config.get("rerank_method", "llm") if config else "llm"  # llm 或 keywords
    
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
        使用LLM对文档重新打分
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            重排序后的文档列表
        """
        try:
            if self.rerank_method == "llm":
                return self._rerank_with_llm(query, documents)
            elif self.rerank_method == "keywords":
                return self._rerank_with_keywords(query, documents)
            else:
                # 默认返回原始文档
                return documents
                
        except Exception as e:
            logger.error(f"[Reranker RAG] 重排序失败: {e}")
            # 失败时返回原始文档
            return documents
    
    def _rerank_with_llm(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        使用LLM相关性评分对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            重排序后的文档列表
        """
        logger.info(f"[Reranker RAG] 使用LLM重排序 {len(documents)} 个文档")
        
        system_prompt = """你是文档相关性评估专家，擅长判断文档与搜索查询的匹配程度。你的任务是根据文档对给定查询的应答质量，给出0到10分的评分。

评分标准：
0-2分：文档完全无关
3-5分：文档含部分相关信息但未直接回答问题
6-8分：文档相关且能部分解答查询
9-10分：文档高度相关且直接准确回答问题

必须仅返回0到10之间的单个整数评分，不要包含任何其他内容。"""
        
        scored_docs = []
        
        for i, doc in enumerate(documents):
            try:
                # 每5个文档显示一次进度
                if i % 5 == 0 and i > 0:
                    logger.info(f"[Reranker RAG] 评分进度: {i}/{len(documents)}")
                
                user_prompt = f"""查询: {query}

文档:
{doc['content'][:500]}

请对文档的相关性进行评分，评分范围为0到10，仅返回一个整数。"""
                
                # 调用LLM评分
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = call_llm(
                    messages=messages,
                    temperature=0.0
                )
                
                # 提取评分
                score_text = response.strip()
                score_match = re.search(r'\b(10|[0-9])\b', score_text)
                
                if score_match:
                    score = float(score_match.group(1))
                else:
                    # 如果提取失败，使用原始相似度分数
                    logger.warning(f"[Reranker RAG] 无法提取评分: '{score_text}'，使用原始分数")
                    score = doc.get("score", 0) * 10
                
                # 保存原始分数和重排序分数
                doc["original_score"] = doc.get("score", 0)
                doc["rerank_score"] = score / 10.0  # 归一化到0-1
                scored_docs.append(doc)
                
            except Exception as e:
                logger.error(f"[Reranker RAG] 文档{i}评分失败: {e}")
                doc["original_score"] = doc.get("score", 0)
                doc["rerank_score"] = doc.get("score", 0)
                scored_docs.append(doc)
        
        # 按重排序分数降序排序
        reranked = sorted(scored_docs, key=lambda x: x["rerank_score"], reverse=True)
        
        logger.info(f"[Reranker RAG] LLM重排序完成")
        return reranked
    
    def _rerank_with_keywords(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        基于关键词匹配对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 候选文档列表
            
        Returns:
            重排序后的文档列表
        """
        logger.info(f"[Reranker RAG] 使用关键词重排序 {len(documents)} 个文档")
        
        # 提取查询中的关键词（长度>2）
        keywords = [word.lower() for word in query.split() if len(word) > 2]
        
        scored_docs = []
        
        for doc in documents:
            content_lower = doc["content"].lower()
            
            # 基础分数从原始相似度开始
            base_score = doc.get("score", 0) * 0.5
            
            # 关键词匹配分数
            keyword_score = 0
            for keyword in keywords:
                if keyword in content_lower:
                    # 每个关键词匹配加0.1分
                    keyword_score += 0.1
                    
                    # 如果在前1/4位置，额外加0.1分
                    first_pos = content_lower.find(keyword)
                    if first_pos < len(content_lower) / 4:
                        keyword_score += 0.1
                    
                    # 根据频率加分（最多0.2）
                    frequency = content_lower.count(keyword)
                    keyword_score += min(0.05 * frequency, 0.2)
            
            # 最终分数
            final_score = base_score + keyword_score
            
            doc["original_score"] = doc.get("score", 0)
            doc["rerank_score"] = final_score
            scored_docs.append(doc)
        
        # 按重排序分数降序排序
        reranked = sorted(scored_docs, key=lambda x: x["rerank_score"], reverse=True)
        
        logger.info(f"[Reranker RAG] 关键词重排序完成")
        return reranked
    
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

