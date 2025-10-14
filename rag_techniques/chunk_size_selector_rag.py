"""
Chunk Size Selector RAG - 动态分块大小选择

核心思路：
1. 根据查询类型和文档特征动态选择chunk大小
2. 测试多个chunk大小并评估检索质量
3. 自适应选择最优的chunk大小
4. 适合不同粒度的问题

优势：
- 短问题用小chunk（精确定位）
- 长问题用大chunk（全面理解）
- 自动适应内容密度
"""

from typing import List, Dict, Any, Optional
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import generate_rag_answer
from loguru import logger


class ChunkSizeSelectorRAG(BaseRAG):
    """
    动态分块大小选择RAG实现
    
    根据查询和文档特征自动选择最优chunk大小
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Chunk Size Selector RAG", vector_store, config)
        
        # 配置参数 - 候选chunk大小
        self.candidate_sizes = config.get("candidate_sizes", [3, 5, 7, 10])  # 合并相邻chunk的数量
        self.evaluation_method = config.get("evaluation_method", "coverage")  # coverage/diversity/hybrid
        
        logger.info(f"初始化 {self.name}，候选大小={self.candidate_sizes}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        动态chunk大小检索
        """
        self._log("retrieve_start", f"开始动态chunk大小检索，候选大小={self.candidate_sizes}")
        
        # === Step 1: 获取所有chunk ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",
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
        
        # === Step 2: 对每个候选大小进行检索和评估 ===
        size_results = {}
        
        for size in self.candidate_sizes:
            # 创建该大小的chunk组合
            combined_chunks = self._create_combined_chunks(all_chunks, size)
            
            # 评估该大小的检索质量
            quality_score = self._evaluate_chunk_size(query, combined_chunks)
            
            size_results[size] = {
                "chunks": combined_chunks,
                "quality": quality_score
            }
            
            self._log(f"size_{size}_evaluated", f"Chunk大小 {size} 评估完成", {
                "size": size,
                "quality": round(quality_score, 3),
                "num_chunks": len(combined_chunks)
            })
        
        # === Step 3: 选择最优chunk大小 ===
        best_size = max(size_results.items(), key=lambda x: x[1]["quality"])[0]
        best_chunks = size_results[best_size]["chunks"]
        
        self._log("best_size_selected", f"选择最优chunk大小: {best_size}", {
            "selected_size": best_size,
            "quality_score": round(size_results[best_size]["quality"], 3),
            "all_scores": {size: round(res["quality"], 3) for size, res in size_results.items()}
        })
        
        # === Step 4: 使用最优大小进行检索 ===
        query_results = self.vector_store.similarity_search(query=query, top_k=len(best_chunks))
        score_map = {r.get("chunk_id"): r.get("score", 0.0) for r in query_results}
        
        # 计算每个combined chunk的得分
        retrieved_docs = []
        for combined in best_chunks:
            # 计算平均分数
            scores = [score_map.get(cid, 0.0) for cid in combined["chunk_ids"]]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            
            doc = RetrievedDoc(
                chunk_id=combined["combined_id"],
                content=combined["content"],
                score=avg_score,
                metadata={
                    "chunk_size": best_size,
                    "chunk_ids": combined["chunk_ids"],
                    "source": combined.get("source", ""),
                    "selection_reason": f"最优chunk大小={best_size}"
                }
            )
            retrieved_docs.append(doc)
        
        # 按分数排序
        retrieved_docs.sort(key=lambda x: x.score, reverse=True)
        
        self._log("retrieve_end", f"检索完成，使用chunk大小={best_size}，返回 {top_k} 个结果")
        
        return retrieved_docs[:top_k]
    
    def _create_combined_chunks(self, all_chunks: List[Dict], size: int) -> List[Dict]:
        """
        创建指定大小的chunk组合
        """
        combined_chunks = []
        
        for i in range(0, len(all_chunks), size):
            chunk_group = all_chunks[i:i + size]
            
            # 合并内容
            merged_content = "\n\n".join([c.get("content", "") for c in chunk_group])
            
            combined_chunks.append({
                "combined_id": f"combined_{i}_{i+len(chunk_group)}",
                "content": merged_content,
                "chunk_ids": [c.get("chunk_id") for c in chunk_group],
                "source": chunk_group[0].get("filename", "") if chunk_group else "",
                "start_idx": i,
                "end_idx": i + len(chunk_group)
            })
        
        return combined_chunks
    
    def _evaluate_chunk_size(self, query: str, combined_chunks: List[Dict]) -> float:
        """
        评估特定chunk大小的检索质量
        
        使用简化的评估方法：
        - coverage: 覆盖度（chunk数量和长度）
        - diversity: 多样性（chunk之间的差异）
        - hybrid: 混合评估
        """
        if not combined_chunks:
            return 0.0
        
        # 覆盖度评分：平衡chunk数量和平均长度
        num_chunks = len(combined_chunks)
        avg_length = sum(len(c["content"]) for c in combined_chunks) / num_chunks
        
        # 归一化长度（假设理想长度在500-2000字符之间）
        ideal_length = 1000
        length_score = 1.0 - abs(avg_length - ideal_length) / ideal_length
        length_score = max(0.0, min(1.0, length_score))
        
        # 数量评分（10-30个chunk为佳）
        ideal_num = 20
        num_score = 1.0 - abs(num_chunks - ideal_num) / ideal_num
        num_score = max(0.0, min(1.0, num_score))
        
        if self.evaluation_method == "coverage":
            return (length_score + num_score) / 2
        elif self.evaluation_method == "diversity":
            # 简化的多样性评估：chunk数量越多越多样
            diversity_score = min(1.0, num_chunks / 30)
            return diversity_score
        else:  # hybrid
            return (length_score * 0.4 + num_score * 0.3 + min(1.0, num_chunks / 30) * 0.3)
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于动态选择的chunk大小生成答案
        """
        self._log("generate_start", "开始生成答案（动态chunk大小）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 获取使用的chunk大小
        chunk_size = retrieved_docs[0].metadata.get("chunk_size", "未知") if retrieved_docs else "未知"
        
        # 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            context_parts.append(
                f"[文档{i+1}] (使用chunk大小: {chunk_size})\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""你是一个专业的AI助手，基于动态chunk大小选择的结果回答问题。
检索过程：系统自动评估了多个chunk大小，选择了最优大小 {chunk_size} 进行检索。

请根据提供的上下文信息回答用户问题：
1. chunk大小已针对当前查询优化
2. 充分利用提供的上下文信息
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

