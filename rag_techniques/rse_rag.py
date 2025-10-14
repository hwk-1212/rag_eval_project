"""
RSE RAG - Relevant Segment Extraction (相关段落提取)

核心思路：
1. 计算每个chunk的"价值"（相关性分数 - 不相关惩罚）
2. 使用最大子数组和算法找到最佳连续段落
3. 提取多个高价值段落而不是孤立的chunk
4. 保持段落的连续性和上下文完整性

优势：
- 连续段落比孤立chunk提供更好的上下文
- 自动过滤低价值内容
- 动态确定检索长度
"""

from typing import List, Dict, Any, Optional
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import generate_rag_answer
from loguru import logger


class RSERAG(BaseRAG):
    """
    RSE (Relevant Segment Extraction) RAG实现
    
    通过计算chunk价值并提取连续段落来改进检索
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("RSE RAG", vector_store, config)
        
        # 配置参数
        self.irrelevant_penalty = config.get("irrelevant_penalty", 0.2)  # 不相关chunk的惩罚
        self.max_segment_length = config.get("max_segment_length", 20)  # 单个段落最大chunk数
        self.total_max_length = config.get("total_max_length", 30)  # 总段落最大chunk数
        self.min_segment_value = config.get("min_segment_value", 0.2)  # 段落最小价值
        
        logger.info(f"初始化 {self.name}，惩罚={self.irrelevant_penalty}, 最大段落长度={self.max_segment_length}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        RSE检索：计算chunk价值并提取最佳连续段落
        """
        self._log("retrieve_start", f"开始RSE检索，top_k={top_k}")
        
        # === Step 1: 获取所有chunk及其相似度分数 ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",  # 获取所有chunk
                top_k=100
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        
        if not all_chunks:
            self._log("retrieve_end", "未找到文档块")
            return []
        
        # 按chunk_id排序
        all_chunks.sort(key=lambda x: x.get("chunk_id", ""))
        
        # === Step 2: 计算与query的相关性分数 ===
        query_results = self.vector_store.similarity_search(query=query, top_k=len(all_chunks))
        
        # 创建chunk_id到score的映射
        score_map = {}
        for result in query_results:
            chunk_id = result.get("chunk_id", "")
            score = result.get("score", 0.0)
            score_map[chunk_id] = score
        
        self._log("relevance_computed", f"计算了 {len(all_chunks)} 个chunk的相关性分数")
        
        # === Step 3: 计算chunk价值（score - penalty） ===
        chunk_values = []
        for chunk in all_chunks:
            chunk_id = chunk.get("chunk_id", "")
            score = score_map.get(chunk_id, 0.0)
            value = score - self.irrelevant_penalty  # 应用惩罚
            chunk_values.append(value)
        
        self._log("values_computed", "计算chunk价值完成", {
            "positive_chunks": sum(1 for v in chunk_values if v > 0),
            "negative_chunks": sum(1 for v in chunk_values if v <= 0)
        })
        
        # === Step 4: 找到最佳连续段落 ===
        best_segments = self._find_best_segments(chunk_values)
        
        self._log("segments_found", f"找到 {len(best_segments)} 个最佳段落", {
            "segment_count": len(best_segments),
            "segments": [f"[{s[0]}:{s[1]}]" for s in best_segments]
        })
        
        # === Step 5: 重建段落为RetrievedDoc ===
        retrieved_docs = self._reconstruct_segments(all_chunks, best_segments, query, score_map)
        
        self._log("retrieve_end", f"RSE检索完成，返回 {len(retrieved_docs)} 个段落")
        
        return retrieved_docs[:top_k]
    
    def _find_best_segments(self, chunk_values: List[float]) -> List[tuple]:
        """
        使用最大子数组和算法找到最佳连续段落
        """
        best_segments = []
        total_included_chunks = 0
        
        # 继续寻找段落直到达到限制
        while total_included_chunks < self.total_max_length:
            best_score = self.min_segment_value
            best_segment = None
            
            # 尝试每个可能的起始位置
            for start in range(len(chunk_values)):
                # 如果该起始位置已在选定段落中，跳过
                if any(start >= s[0] and start < s[1] for s in best_segments):
                    continue
                
                # 尝试每个可能的段落长度
                for length in range(1, min(self.max_segment_length, len(chunk_values) - start) + 1):
                    end = start + length
                    
                    # 如果结束位置已在选定段落中，跳过
                    if any(end > s[0] and end <= s[1] for s in best_segments):
                        continue
                    
                    # 计算段落价值（chunk价值的总和）
                    segment_value = sum(chunk_values[start:end])
                    
                    # 更新最佳段落
                    if segment_value > best_score:
                        best_score = segment_value
                        best_segment = (start, end)
            
            # 如果找到好的段落，添加它
            if best_segment:
                best_segments.append(best_segment)
                total_included_chunks += best_segment[1] - best_segment[0]
                logger.debug(f"找到段落 [{best_segment[0]}:{best_segment[1]}]，得分 {best_score:.4f}")
            else:
                # 没有更多好段落
                break
        
        # 按起始位置排序
        best_segments.sort(key=lambda x: x[0])
        
        return best_segments
    
    def _reconstruct_segments(
        self, 
        all_chunks: List[Dict], 
        best_segments: List[tuple],
        query: str,
        score_map: Dict[str, float]
    ) -> List[RetrievedDoc]:
        """
        从最佳段落重建RetrievedDoc对象
        """
        retrieved_docs = []
        
        for seg_idx, (start, end) in enumerate(best_segments):
            # 获取该段落的chunks
            segment_chunks = all_chunks[start:end]
            
            # 合并文本
            merged_content = "\n\n".join([c.get("content", "") for c in segment_chunks])
            
            # 计算段落的平均分数
            segment_scores = [score_map.get(c.get("chunk_id", ""), 0.0) for c in segment_chunks]
            avg_score = sum(segment_scores) / len(segment_scores) if segment_scores else 0.0
            
            # 构造唯一的segment ID
            segment_id = f"segment_{start}_{end}"
            
            doc = RetrievedDoc(
                chunk_id=segment_id,
                content=merged_content,
                score=avg_score,
                metadata={
                    "segment_range": (start, end),
                    "segment_length": end - start,
                    "chunk_ids": [c.get("chunk_id") for c in segment_chunks],
                    "source": segment_chunks[0].get("filename", "") if segment_chunks else "",
                    "segment_index": seg_idx
                }
            )
            retrieved_docs.append(doc)
        
        return retrieved_docs
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于连续段落生成答案
        """
        self._log("generate_start", "开始生成答案（RSE）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文，标注段落信息
        context_parts = []
        for doc in retrieved_docs:
            seg_range = doc.metadata.get("segment_range", (0, 0))
            seg_len = doc.metadata.get("segment_length", 0)
            context_parts.append(
                f"[段落{doc.metadata.get('segment_index', 0)+1}] (Chunks {seg_range[0]}-{seg_range[1]-1}, 长度={seg_len})\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = """你是一个专业的AI助手，基于RSE（相关段落提取）检索的结果回答问题。
检索过程：通过计算chunk价值，自动提取了最相关的连续文本段落。

请根据提供的段落信息回答用户问题：
1. 每个段落都是经过价值评估的连续文本
2. 充分利用段落的连贯性
3. 保持回答的准确性和完整性"""
        
        try:
            context_list = [doc.content for doc in retrieved_docs]
            answer = generate_rag_answer(
                query=query,
                context=context_list,
                system_prompt=system_prompt
            )
            self._log("generate_end", f"答案生成完成，长度={len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return f"生成答案时出错：{str(e)}"

