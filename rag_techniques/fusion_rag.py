from typing import List, Dict, Any, Optional
from loguru import logger
from rank_bm25 import BM25Okapi
import jieba
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer


class FusionRAG(BaseRAG):
    """Fusion RAG - 融合向量检索和BM25关键词检索
    
    流程：
    1. 并行执行向量检索和BM25检索
    2. 对两种检索结果进行分数归一化
    3. 加权融合两种检索分数
    4. 根据融合分数重新排序
    5. 返回top_k文档
    
    优势：
    - 结合语义理解和关键词匹配
    - 适应不同类型的查询
    - 提高检索鲁棒性
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Fusion RAG", vector_store, config)
        self.vector_weight = config.get("vector_weight", 0.5) if config else 0.5
        self.bm25_weight = config.get("bm25_weight", 0.5) if config else 0.5
        self.system_prompt = config.get("system_prompt") if config else None
        
        # BM25索引（延迟初始化）
        self.bm25 = None
        self.bm25_corpus = []
        self.bm25_docs_map = {}
    
    def _build_bm25_index(self, documents: List[Dict]):
        """构建BM25索引"""
        try:
            self._log("bm25_index_start", "开始构建BM25索引", {
                "doc_count": len(documents)
            })
            
            # 提取文档内容
            self.bm25_corpus = []
            self.bm25_docs_map = {}
            
            total_tokens = 0
            for i, doc in enumerate(documents):
                content = doc["content"]
                # 使用jieba分词
                tokens = list(jieba.cut(content))
                self.bm25_corpus.append(tokens)
                self.bm25_docs_map[i] = doc
                total_tokens += len(tokens)
            
            # 创建BM25索引
            self.bm25 = BM25Okapi(self.bm25_corpus)
            
            self._log("bm25_index_complete", "BM25索引构建完成", {
                "doc_count": len(self.bm25_corpus),
                "total_tokens": total_tokens,
                "avg_tokens_per_doc": round(total_tokens / len(self.bm25_corpus), 2) if self.bm25_corpus else 0
            })
            
            logger.info(f"[Fusion RAG] BM25索引构建完成，文档数: {len(self.bm25_corpus)}")
            
        except Exception as e:
            self._log("bm25_index_error", f"BM25索引构建失败: {str(e)}", {"error": str(e)})
            logger.error(f"[Fusion RAG] BM25索引构建失败: {e}")
            self.bm25 = None
    
    def _bm25_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        BM25关键词检索
        
        Args:
            query: 查询文本
            top_k: 返回文档数
            
        Returns:
            检索结果列表
        """
        try:
            if self.bm25 is None:
                self._log("bm25_search_skip", "BM25索引未初始化，跳过BM25检索")
                logger.warning("[Fusion RAG] BM25索引未初始化")
                return []
            
            # 查询分词
            query_tokens = list(jieba.cut(query))
            self._log("bm25_search_tokenize", "查询分词完成", {
                "query": query[:50] + "..." if len(query) > 50 else query,
                "tokens": query_tokens[:10],  # 只显示前10个token
                "token_count": len(query_tokens)
            })
            
            # BM25检索
            scores = self.bm25.get_scores(query_tokens)
            
            # 获取top_k
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            
            results = []
            for idx in top_indices:
                if idx in self.bm25_docs_map:
                    doc = self.bm25_docs_map[idx].copy()
                    doc["bm25_score"] = float(scores[idx])
                    results.append(doc)
            
            self._log("bm25_search_complete", f"BM25检索完成", {
                "result_count": len(results),
                "top_scores": [round(doc["bm25_score"], 4) for doc in results[:3]]
            })
            
            logger.info(f"[Fusion RAG] BM25检索到 {len(results)} 个文档")
            return results
            
        except Exception as e:
            self._log("bm25_search_error", f"BM25检索失败: {str(e)}", {"error": str(e)})
            logger.error(f"[Fusion RAG] BM25检索失败: {e}")
            return []
    
    def _normalize_scores(self, docs: List[Dict], score_key: str) -> List[Dict]:
        """分数归一化到[0,1]"""
        if not docs:
            return docs
        
        scores = [doc.get(score_key, 0) for doc in docs]
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 1
        
        # 避免除零
        score_range = max_score - min_score
        if score_range == 0:
            score_range = 1
        
        for doc in docs:
            original = doc.get(score_key, 0)
            normalized = (original - min_score) / score_range
            doc[f"{score_key}_normalized"] = normalized
        
        return docs
    
    def _fusion_results(
        self,
        vector_results: List[Dict],
        bm25_results: List[Dict],
        top_k: int
    ) -> List[Dict]:
        """
        融合两种检索结果
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            top_k: 最终返回数量
            
        Returns:
            融合后的结果
        """
        self._log("fusion_start", "开始融合向量和BM25结果", {
            "vector_count": len(vector_results),
            "bm25_count": len(bm25_results),
            "vector_weight": self.vector_weight,
            "bm25_weight": self.bm25_weight
        })
        
        # 归一化分数
        vector_results = self._normalize_scores(vector_results, "score")
        bm25_results = self._normalize_scores(bm25_results, "bm25_score")
        
        self._log("fusion_normalize", "分数归一化完成", {
            "vector_normalized": len(vector_results),
            "bm25_normalized": len(bm25_results)
        })
        
        # 创建文档ID到分数的映射
        fusion_scores = {}
        
        # 添加向量检索分数
        for doc in vector_results:
            chunk_id = doc["chunk_id"]
            vector_score = doc.get("score_normalized", 0)
            fusion_scores[chunk_id] = {
                "doc": doc,
                "vector_score": vector_score,
                "bm25_score": 0,
                "fusion_score": 0
            }
        
        # 添加BM25分数
        overlap_count = 0
        for doc in bm25_results:
            chunk_id = doc["chunk_id"]
            bm25_score = doc.get("bm25_score_normalized", 0)
            
            if chunk_id in fusion_scores:
                fusion_scores[chunk_id]["bm25_score"] = bm25_score
                overlap_count += 1
            else:
                fusion_scores[chunk_id] = {
                    "doc": doc,
                    "vector_score": 0,
                    "bm25_score": bm25_score,
                    "fusion_score": 0
                }
        
        self._log("fusion_merge", "结果合并完成", {
            "total_unique_docs": len(fusion_scores),
            "overlap_docs": overlap_count,
            "vector_only": len(vector_results) - overlap_count,
            "bm25_only": len(bm25_results) - overlap_count
        })
        
        # 计算融合分数
        for chunk_id, scores in fusion_scores.items():
            fusion_score = (
                self.vector_weight * scores["vector_score"] +
                self.bm25_weight * scores["bm25_score"]
            )
            scores["fusion_score"] = fusion_score
            scores["doc"]["fusion_score"] = fusion_score
            scores["doc"]["vector_score_normalized"] = scores["vector_score"]
            scores["doc"]["bm25_score_normalized"] = scores["bm25_score"]
        
        # 按融合分数排序
        sorted_results = sorted(
            fusion_scores.values(),
            key=lambda x: x["fusion_score"],
            reverse=True
        )
        
        # 返回top_k
        final_docs = [item["doc"] for item in sorted_results[:top_k]]
        
        self._log("fusion_complete", f"融合排序完成，返回top {top_k}文档", {
            "final_count": len(final_docs),
            "top_fusion_scores": [round(item["fusion_score"], 4) for item in sorted_results[:3]]
        })
        
        logger.info(f"[Fusion RAG] 融合完成，返回 {len(final_docs)} 个文档")
        return final_docs
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        融合检索
        
        Args:
            query: 查询文本
            top_k: 返回文档数
            
        Returns:
            融合后的文档列表
        """
        try:
            # Step 1: 向量检索
            self._log("vector_search_start", f"开始向量检索，top_k={top_k * 2}")
            vector_results = self.vector_store.similarity_search(
                query=query,
                top_k=top_k * 2  # 获取更多候选
            )
            
            if not vector_results:
                self._log("vector_search_empty", "向量检索未找到文档")
                logger.warning("[Fusion RAG] 向量检索未找到文档")
                return []
            
            self._log("vector_search_complete", f"向量检索完成", {
                "result_count": len(vector_results),
                "top_scores": [round(r["score"], 4) for r in vector_results[:3]]
            })
            
            # Step 2: 构建BM25索引（如果还没有）
            if self.bm25 is None:
                self._build_bm25_index(vector_results)
            else:
                self._log("bm25_index_exists", "使用已存在的BM25索引")
            
            # Step 3: BM25检索
            bm25_results = self._bm25_search(query, top_k * 2)
            
            # Step 4: 融合结果
            fused_docs = self._fusion_results(vector_results, bm25_results, top_k)
            
            # Step 5: 转换为RetrievedDoc对象
            self._log("convert_docs_start", "转换为RetrievedDoc对象")
            retrieved_docs = []
            for idx, doc in enumerate(fused_docs):
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],
                    score=doc.get("fusion_score", 0),
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "vector_score": doc.get("vector_score_normalized", 0),
                        "bm25_score": doc.get("bm25_score_normalized", 0),
                        "fusion_score": doc.get("fusion_score", 0),
                    }
                )
                retrieved_docs.append(retrieved_doc)
                
                # 记录前3个文档的详细信息
                if idx < 3:
                    self._log(f"fusion_doc_{idx+1}", f"融合文档 #{idx+1}", {
                        "filename": doc.get("filename", "Unknown"),
                        "fusion_score": round(doc.get("fusion_score", 0), 4),
                        "vector_score": round(doc.get("vector_score_normalized", 0), 4),
                        "bm25_score": round(doc.get("bm25_score_normalized", 0), 4),
                        "content_length": len(doc["content"])
                    })
            
            logger.info(f"[Fusion RAG] 检索完成，返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            self._log("retrieve_error", f"检索失败: {str(e)}", {"error": str(e)})
            logger.error(f"[Fusion RAG] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """生成答案"""
        try:
            if not retrieved_docs:
                self._log("generate_no_docs", "没有检索到文档，返回默认回答")
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 准备上下文
            self._log("generate_prepare_context", "准备融合文档上下文", {
                "doc_count": len(retrieved_docs),
                "total_context_length": sum(len(doc.content) for doc in retrieved_docs),
                "avg_fusion_score": round(sum(doc.score for doc in retrieved_docs) / len(retrieved_docs), 4)
            })
            
            context = [doc.content for doc in retrieved_docs]
            
            # 调用LLM
            self._log("generate_llm_call", "调用LLM生成答案")
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            self._log("generate_complete", "答案生成成功", {
                "answer_length": len(answer),
                "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer
            })
            
            logger.info(f"[Fusion RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            self._log("generate_error", f"生成答案失败: {str(e)}", {"error": str(e)})
            logger.error(f"[Fusion RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

