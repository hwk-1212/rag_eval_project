"""
Hierarchical Indices RAG - 层次化索引RAG

核心思路：
1. 两级索引结构：摘要层 + 详细块层
2. 为文档的每个部分生成摘要，创建摘要索引
3. 检索时先在摘要层查找相关部分
4. 然后在相关部分的详细块中精确检索
5. 适合大规模文档库的快速定位

优势：
- 减少检索空间，提高效率
- 先粗后细，逐步聚焦
- 保持语义连贯性
"""

from typing import List, Dict, Any, Optional
import time
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import call_llm, generate_rag_answer
from backend.utils.embedding import get_single_embedding
from loguru import logger


class HierarchicalRAG(BaseRAG):
    """
    层次化索引RAG实现
    
    两级检索：
    1. Level 1: 在文档摘要层检索（粗粒度）
    2. Level 2: 在匹配部分的详细块中检索（细粒度）
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Hierarchical Indices RAG", vector_store, config)
        
        # 摘要层参数
        self.k_summaries = config.get("k_summaries", 3)  # 检索多少个摘要
        self.summary_chunk_size = config.get("summary_chunk_size", 5)  # 每个摘要包含多少个原始chunk
        
        # 详细层参数
        self.k_chunks_per_summary = config.get("k_chunks_per_summary", 3)  # 每个摘要下检索多少个详细块
        
        self.enable_summary_cache = config.get("enable_summary_cache", True)
        self._summary_cache = {}  # 缓存生成的摘要
        
        logger.info(f"初始化 {self.name}，摘要数={self.k_summaries}，每摘要块数={self.k_chunks_per_summary}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        分层检索：先检索摘要层，再检索详细层
        """
        self._log("retrieve_start", f"开始分层检索，k_summaries={self.k_summaries}, k_per_summary={self.k_chunks_per_summary}")
        
        # === Step 1: 构建摘要层索引 ===
        summaries = self._build_summary_index()
        self._log("summary_build", f"构建了 {len(summaries)} 个摘要块", {"summary_count": len(summaries)})
        
        # === Step 2: 在摘要层检索相关部分 ===
        relevant_summaries = self._retrieve_summaries(query, summaries)
        self._log("summary_retrieve", f"检索到 {len(relevant_summaries)} 个相关摘要", {
            "retrieved_count": len(relevant_summaries),
            "summary_scores": [round(s["score"], 3) for s in relevant_summaries]
        })
        
        # === Step 3: 从相关摘要对应的详细块中检索 ===
        detailed_docs = self._retrieve_detailed_chunks(query, relevant_summaries)
        self._log("retrieve_end", f"从详细层检索到 {len(detailed_docs)} 个文档块", {
            "detailed_count": len(detailed_docs),
            "avg_score": round(sum(d.score for d in detailed_docs) / len(detailed_docs), 3) if detailed_docs else 0
        })
        
        return detailed_docs[:top_k]
    
    def _build_summary_index(self) -> List[Dict[str, Any]]:
        """
        构建摘要层索引
        将连续的chunk合并成组，并为每组生成摘要
        """
        # 获取所有chunk - 使用一个通用查询获取所有文档
        # Milvus需要一个query，我们使用第一个chunk的查询来获取集合统计
        try:
            # 尝试获取前100个chunk（足够用于摘要构建）
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",  # 使用通用查询
                top_k=100
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        
        if not all_chunks:
            logger.warning("向量库为空，无法构建摘要索引")
            return []
        
        # 按chunk_id排序（假设chunk_id是连续的）
        all_chunks.sort(key=lambda x: x.get("chunk_id", ""))
        
        summaries = []
        
        # 将chunks分组，每组summary_chunk_size个
        for i in range(0, len(all_chunks), self.summary_chunk_size):
            chunk_group = all_chunks[i:i + self.summary_chunk_size]
            
            # 为这组chunk生成摘要
            summary_text = self._generate_summary_for_group(chunk_group)
            
            summaries.append({
                "summary_text": summary_text,
                "chunk_ids": [c.get("chunk_id") for c in chunk_group],
                "chunk_indices": list(range(i, min(i + self.summary_chunk_size, len(all_chunks)))),
                "original_chunks": chunk_group
            })
        
        return summaries
    
    def _generate_summary_for_group(self, chunk_group: List[Dict]) -> str:
        """
        为一组chunk生成摘要
        """
        # 检查缓存
        chunk_ids = [c.get("chunk_id", "") for c in chunk_group]
        cache_key = "_".join(chunk_ids)
        
        if self.enable_summary_cache and cache_key in self._summary_cache:
            return self._summary_cache[cache_key]
        
        # 合并chunk文本（注意：vector_store返回的字段是content，不是text）
        combined_text = "\n\n".join([c.get("content", "") for c in chunk_group])
        
        # 使用LLM生成摘要
        system_prompt = """你是一个专业的文档摘要系统。
请为提供的文本生成一个简洁但全面的摘要。
摘要应该：
1. 捕捉主要内容和关键信息
2. 保持逻辑连贯
3. 长度控制在200-300字
4. 不要添加任何不在原文中的信息"""
        
        user_prompt = f"请为以下文本生成摘要：\n\n{combined_text[:4000]}"  # 限制长度
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            summary = call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=500
            )
            
            # 缓存摘要
            if self.enable_summary_cache:
                self._summary_cache[cache_key] = summary
            
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {e}")
            # 降级：使用前200字作为摘要
            return combined_text[:200] + "..."
    
    def _retrieve_summaries(self, query: str, summaries: List[Dict]) -> List[Dict]:
        """
        在摘要层检索相关摘要
        """
        if not summaries:
            return []
        
        # 为query生成embedding
        query_embedding = self._get_embedding(query)
        
        # 为每个摘要计算相似度
        summary_scores = []
        for i, summary_item in enumerate(summaries):
            summary_text = summary_item["summary_text"]
            summary_embedding = self._get_embedding(summary_text)
            
            # 计算余弦相似度
            score = self._cosine_similarity(query_embedding, summary_embedding)
            summary_scores.append({
                "index": i,
                "score": score,
                **summary_item
            })
        
        # 按分数排序
        summary_scores.sort(key=lambda x: x["score"], reverse=True)
        
        return summary_scores[:self.k_summaries]
    
    def _retrieve_detailed_chunks(self, query: str, relevant_summaries: List[Dict]) -> List[RetrievedDoc]:
        """
        在相关摘要对应的详细块中检索
        """
        all_retrieved_docs = []
        
        for summary in relevant_summaries:
            chunk_ids = summary["chunk_ids"]
            
            # 在这些chunk中进行精确检索
            for chunk_id in chunk_ids:
                # 使用vector_store的get_by_chunk_id方法
                chunks = self.vector_store.get_by_chunk_id(chunk_id)
                
                if chunks:
                    chunk_data = chunks[0]
                    
                    # vector_store.get_by_chunk_id 不返回embedding
                    # 我们使用摘要的分数作为基准，并根据chunk在摘要中的位置调整
                    score = summary["score"] * 0.9
                    
                    doc = RetrievedDoc(
                        chunk_id=chunk_id,
                        content=chunk_data.get("content", ""),
                        score=score,
                        metadata={
                            "source": chunk_data.get("filename", ""),
                            "summary": summary["summary_text"],
                            "from_summary_rank": relevant_summaries.index(summary) + 1
                        }
                    )
                    all_retrieved_docs.append(doc)
        
        # 按分数排序
        all_retrieved_docs.sort(key=lambda x: x.score, reverse=True)
        
        # 返回top k_chunks_per_summary * k_summaries
        total_k = self.k_chunks_per_summary * self.k_summaries
        return all_retrieved_docs[:total_k]
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的embedding"""
        try:
            return get_single_embedding(text)
        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于分层检索的结果生成答案
        """
        self._log("generate_start", "开始生成答案（分层检索）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文，包含摘要信息
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            summary = doc.metadata.get("summary", "")
            context_parts.append(
                f"[文档{i+1}] (摘要: {summary[:100]}...)\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""你是一个专业的AI助手，基于分层检索的结果回答问题。
检索过程：先在文档摘要层定位相关部分，再在详细块中精确检索。

请根据提供的上下文信息回答用户问题：
1. 优先使用检索到的详细信息
2. 结合摘要理解整体语境
3. 如果信息不足，请明确说明
4. 保持回答的准确性和完整性"""
        
        user_prompt = f"上下文信息：\n{context}\n\n用户问题：{query}\n\n请回答："
        
        try:
            # 使用通用的RAG答案生成函数
            context = [doc.content for doc in retrieved_docs]
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=system_prompt
            )
            self._log("generate_end", f"答案生成完成，长度={len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return f"生成答案时出错：{str(e)}"

