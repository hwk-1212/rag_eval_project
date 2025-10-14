"""
Semantic Chunking RAG - 语义分块RAG

核心思路：
1. 传统分块：固定长度分割，可能在语义边界切断
2. 语义分块：基于语义相似度动态确定分块边界
3. 在检索时考虑chunk间的语义连贯性
4. 当检索到一个chunk时，检查其相邻chunk是否语义相关
5. 如果相关，则合并返回，保持语义完整性

优势：
- 保持语义完整性
- 避免关键信息被分割
- 动态扩展上下文
- 更符合自然语义边界
"""

from typing import List, Dict, Any, Optional
import numpy as np
from .base import BaseRAG, RetrievedDoc, RagResult
from loguru import logger


class SemanticChunkingRAG(BaseRAG):
    """
    语义分块RAG实现
    
    基于语义相似度动态确定检索范围，保持语义完整性
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Semantic Chunking RAG", vector_store, config)
        
        # 配置参数
        self.similarity_threshold = config.get("similarity_threshold", 0.7)  # 相邻chunk相似度阈值
        self.max_expand_chunks = config.get("max_expand_chunks", 2)  # 最多向前/后扩展几个chunk
        self.breakpoint_method = config.get("breakpoint_method", "percentile")  # percentile/standard_deviation/interquartile
        self.breakpoint_threshold = config.get("breakpoint_threshold", 70)  # 阈值
        
        logger.info(f"初始化 {self.name}，相似度阈值={self.similarity_threshold}, 最大扩展={self.max_expand_chunks}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        语义感知检索：基于语义边界动态扩展检索范围
        """
        self._log("retrieve_start", f"开始语义分块检索，top_k={top_k}")
        
        # === Step 1: 初始向量检索 ===
        initial_results = self.vector_store.similarity_search(query=query, top_k=top_k * 2)
        self._log("initial_search", f"初始检索到 {len(initial_results)} 个候选文档", {
            "candidate_count": len(initial_results)
        })
        
        if not initial_results:
            return []
        
        # === Step 2: 获取所有chunk（用于查找相邻chunk） ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",  # 使用通用查询
                top_k=100
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        chunk_map = {c.get("chunk_id"): c for c in all_chunks}
        
        # 按chunk_id排序构建索引
        sorted_chunk_ids = sorted(chunk_map.keys())
        chunk_index = {cid: idx for idx, cid in enumerate(sorted_chunk_ids)}
        
        self._log("chunks_indexed", f"构建了 {len(sorted_chunk_ids)} 个chunk的索引")
        
        # === Step 3: 对每个初始结果，基于语义相似度扩展上下文 ===
        expanded_results = []
        for result in initial_results:
            expanded_doc = self._expand_semantic_context(
                result, 
                chunk_map, 
                sorted_chunk_ids, 
                chunk_index,
                query
            )
            expanded_results.append(expanded_doc)
        
        # === Step 4: 去重（相同的扩展结果） ===
        unique_results = self._deduplicate_results(expanded_results)
        
        self._log("retrieve_end", f"语义扩展完成，返回 {len(unique_results)} 个文档", {
            "expanded_count": len(unique_results),
            "avg_chunks_per_result": round(sum(len(r.metadata.get("merged_chunk_ids", [])) for r in unique_results) / len(unique_results), 2) if unique_results else 0
        })
        
        return unique_results[:top_k]
    
    def _expand_semantic_context(
        self, 
        center_chunk: Dict, 
        chunk_map: Dict, 
        sorted_chunk_ids: List[str], 
        chunk_index: Dict,
        query: str
    ) -> RetrievedDoc:
        """
        基于chunk位置和分数扩展中心chunk的上下文
        注：由于vector_store不返回embedding，我们基于chunk_id的连续性和分数衰减来扩展
        """
        center_id = center_chunk.get("chunk_id")
        center_score = center_chunk.get("score", 0.5)
        
        if center_id not in chunk_index:
            # 无法扩展，直接返回
            return RetrievedDoc(
                content=center_chunk.get("content", ""),
                score=center_score,
                metadata={
                    "chunk_id": center_id,
                    "source": center_chunk.get("filename", ""),
                    "merged_chunk_ids": [center_id],
                    "expansion": "none"
                }
            )
        
        center_idx = chunk_index[center_id]
        
        # 向前扩展（相邻chunk，分数递减）
        prev_chunks = []
        for i in range(1, self.max_expand_chunks + 1):
            prev_idx = center_idx - i
            if prev_idx < 0:
                break
            
            prev_id = sorted_chunk_ids[prev_idx]
            prev_chunk = chunk_map.get(prev_id)
            
            if not prev_chunk:
                break
            
            # 使用分数衰减策略：越远分数越低
            decay_factor = 1.0 - (i * 0.2)  # 每远一个chunk，分数降20%
            similarity = center_score * decay_factor
            
            if similarity >= self.similarity_threshold * center_score:
                prev_chunks.insert(0, {
                    "chunk": prev_chunk,
                    "similarity": similarity
                })
            else:
                # 分数太低，停止扩展
                break
        
        # 向后扩展
        next_chunks = []
        for i in range(1, self.max_expand_chunks + 1):
            next_idx = center_idx + i
            if next_idx >= len(sorted_chunk_ids):
                break
            
            next_id = sorted_chunk_ids[next_idx]
            next_chunk = chunk_map.get(next_id)
            
            if not next_chunk:
                break
            
            # 使用分数衰减策略
            decay_factor = 1.0 - (i * 0.2)
            similarity = center_score * decay_factor
            
            if similarity >= self.similarity_threshold * center_score:
                next_chunks.append({
                    "chunk": next_chunk,
                    "similarity": similarity
                })
            else:
                # 分数太低，停止扩展
                break
        
        # 合并文本（注意：vector_store返回的字段是content，不是text）
        merged_chunks = prev_chunks + [{"chunk": center_chunk, "similarity": center_score}] + next_chunks
        merged_text = "\n\n".join([item["chunk"].get("content", "") for item in merged_chunks])
        merged_ids = [item["chunk"].get("chunk_id") for item in merged_chunks]
        
        # 计算加权平均分数（基于各chunk的相似度）
        if merged_chunks:
            final_score = sum(item["similarity"] for item in merged_chunks) / len(merged_chunks)
        else:
            final_score = center_score
        
        return RetrievedDoc(
            content=merged_text,
            score=final_score,
            metadata={
                "chunk_id": center_id,
                "source": center_chunk.get("filename", ""),
                "merged_chunk_ids": merged_ids,
                "expansion": f"prev={len(prev_chunks)}, next={len(next_chunks)}",
                "semantic_similarities": [round(item["similarity"], 3) for item in merged_chunks]
            }
        )
    
    def _deduplicate_results(self, results: List[RetrievedDoc]) -> List[RetrievedDoc]:
        """
        去重：如果两个结果的merged_chunk_ids有重叠，保留分数更高的
        """
        unique_results = []
        seen_chunk_sets = []
        
        # 按分数排序
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        for result in sorted_results:
            merged_ids = set(result.metadata.get("merged_chunk_ids", []))
            
            # 检查是否与已有结果重叠
            is_duplicate = False
            for seen_set in seen_chunk_sets:
                overlap = len(merged_ids & seen_set)
                overlap_ratio = overlap / len(merged_ids) if len(merged_ids) > 0 else 0
                
                if overlap_ratio > 0.5:  # 重叠超过50%认为是重复
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_results.append(result)
                seen_chunk_sets.append(merged_ids)
        
        return unique_results
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的embedding"""
        try:
            response = self.llm_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            return []
    
    def _compute_breakpoints(self, similarities: List[float], method: str = "percentile", threshold: float = 70) -> List[int]:
        """
        根据相似度下降计算分块的断点
        
        Args:
            similarities: 句子之间的相似度分数列表
            method: 'percentile'（百分位）、'standard_deviation'（标准差）或 'interquartile'（四分位距）
            threshold: 阈值
        
        Returns:
            分块的索引列表
        """
        if not similarities:
            return []
        
        # 根据选定的方法确定阈值
        if method == "percentile":
            threshold_value = np.percentile(similarities, threshold)
        elif method == "standard_deviation":
            mean = np.mean(similarities)
            std_dev = np.std(similarities)
            threshold_value = mean - (threshold * std_dev)
        elif method == "interquartile":
            q1, q3 = np.percentile(similarities, [25, 75])
            threshold_value = q1 - 1.5 * (q3 - q1)
        else:
            raise ValueError("Invalid method. Choose 'percentile', 'standard_deviation', or 'interquartile'.")
        
        # 找出相似度低于阈值的索引
        return [i for i, sim in enumerate(similarities) if sim < threshold_value]
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于语义完整的文档块生成答案
        """
        self._log("generate_start", "开始生成答案（语义分块）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文，标注语义扩展信息
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            expansion_info = doc.metadata.get("expansion", "none")
            merged_count = len(doc.metadata.get("merged_chunk_ids", []))
            
            context_parts.append(
                f"[文档{i+1}] (语义扩展: {expansion_info}, 合并块数: {merged_count})\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""你是一个专业的AI助手，基于语义分块检索的结果回答问题。
检索过程：不是固定长度分块，而是基于语义相似度动态确定块边界，保持语义完整性。

请根据提供的上下文信息回答用户问题：
1. 文档块已经基于语义边界扩展，内容更完整
2. 注意"合并块数"，表示该文档由多少个原始块组成
3. 充分利用完整的语义上下文"""
        
        user_prompt = f"上下文信息：\n{context}\n\n用户问题：{query}\n\n请回答："
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content.strip()
            self._log("generate_end", f"答案生成完成，长度={len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return f"生成答案时出错：{str(e)}"

