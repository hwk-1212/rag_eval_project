from typing import List, Dict, Any, Optional
from loguru import logger
import re
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer, call_llm


class CRAG(BaseRAG):
    """CRAG (Corrective RAG) - 纠错型检索增强生成
    
    流程：
    1. 初始检索获取候选文档
    2. 使用LLM评估每个文档的相关性（0-1分）
    3. 根据最高相关性分数决定策略：
       - 高相关性 (>0.7): 直接使用文档
       - 中相关性 (0.4-0.7): 精炼知识后使用
       - 低相关性 (<0.4): 查询重写后重新检索
    4. 生成答案
    
    优势：
    - 自动纠错，提升答案准确性
    - 动态策略选择，适应不同查询质量
    - 知识精炼减少冗余信息
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("CRAG", vector_store, config)
        self.high_threshold = config.get("high_threshold", 0.7) if config else 0.7
        self.low_threshold = config.get("low_threshold", 0.4) if config else 0.4
        self.max_retries = config.get("max_retries", 1) if config else 1
        self.system_prompt = config.get("system_prompt") if config else None
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        使用CRAG策略检索文档
        
        Args:
            query: 查询文本
            top_k: 返回文档数量
            
        Returns:
            经过纠错处理的文档列表
        """
        try:
            logger.info(f"[CRAG] 开始处理查询")
            
            # Step 1: 初始检索
            candidates = self.vector_store.similarity_search(
                query=query,
                top_k=top_k * 2  # 获取更多候选文档
            )
            
            if not candidates:
                logger.warning(f"[CRAG] 未找到候选文档")
                return []
            
            logger.info(f"[CRAG] 初始检索到 {len(candidates)} 个候选文档")
            
            # Step 2: 评估文档相关性
            evaluated_docs = self._evaluate_relevance(query, candidates)
            
            # Step 3: 根据最高相关性决定策略
            max_relevance = max([doc["relevance"] for doc in evaluated_docs])
            logger.info(f"[CRAG] 最高相关性: {max_relevance:.2f}")
            
            final_docs = []
            
            if max_relevance > self.high_threshold:
                # 策略1: 高相关性 - 直接使用
                logger.info(f"[CRAG] 策略: 高相关性，直接使用文档")
                final_docs = [doc for doc in evaluated_docs if doc["relevance"] > self.high_threshold]
                final_docs = final_docs[:top_k]
                
            elif max_relevance < self.low_threshold:
                # 策略2: 低相关性 - 查询重写后重新检索
                logger.info(f"[CRAG] 策略: 低相关性，查询重写")
                rewritten_query = self._rewrite_query(query)
                logger.info(f"[CRAG] 重写后查询: {rewritten_query}")
                
                # 重新检索
                new_candidates = self.vector_store.similarity_search(
                    query=rewritten_query,
                    top_k=top_k * 2
                )
                
                if new_candidates:
                    evaluated_docs = self._evaluate_relevance(rewritten_query, new_candidates)
                    final_docs = sorted(evaluated_docs, key=lambda x: x["relevance"], reverse=True)[:top_k]
                else:
                    # 如果重写后还是没有，使用原始结果
                    final_docs = sorted(evaluated_docs, key=lambda x: x["relevance"], reverse=True)[:top_k]
                    
            else:
                # 策略3: 中等相关性 - 精炼知识
                logger.info(f"[CRAG] 策略: 中等相关性，精炼知识")
                # 选择相关性最高的文档
                sorted_docs = sorted(evaluated_docs, key=lambda x: x["relevance"], reverse=True)
                final_docs = sorted_docs[:top_k]
                
                # 精炼每个文档的内容
                for doc in final_docs:
                    refined_content = self._refine_knowledge(doc["content"])
                    doc["content"] = refined_content
                    doc["refined"] = True
            
            # 转换为RetrievedDoc对象
            retrieved_docs = []
            for doc in final_docs:
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],
                    score=doc["relevance"],  # 使用相关性分数
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "original_score": doc.get("score", 0),
                        "relevance_score": doc.get("relevance", 0),
                        "refined": doc.get("refined", False),
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            logger.info(f"[CRAG] 最终返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[CRAG] 检索失败: {e}")
            return []
    
    def _evaluate_relevance(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        评估文档与查询的相关性
        
        Args:
            query: 查询文本
            documents: 文档列表
            
        Returns:
            带有relevance评分的文档列表
        """
        logger.info(f"[CRAG] 评估 {len(documents)} 个文档的相关性")
        
        system_prompt = """你是文档相关性评估专家。
请评估文档与查询的相关性，给出0到1之间的分数：
- 0-0.3: 完全不相关或几乎无关
- 0.4-0.7: 部分相关，包含一些有用信息
- 0.8-1.0: 高度相关，直接回答问题

仅返回一个0到1之间的浮点数，不要有任何其他内容。"""
        
        evaluated = []
        
        for i, doc in enumerate(documents):
            try:
                user_prompt = f"""查询: {query}

文档:
{doc['content'][:600]}

相关性评分(0-1):"""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                response = call_llm(
                    messages=messages,
                    temperature=0.0,
                    max_tokens=10
                )
                
                # 提取分数
                score_text = response.strip()
                score_match = re.search(r'(\d+(\.\d+)?)', score_text)
                
                if score_match:
                    relevance = float(score_match.group(1))
                    relevance = min(max(relevance, 0.0), 1.0)  # 限制在0-1范围
                else:
                    logger.warning(f"[CRAG] 无法提取相关性分数: '{score_text}'")
                    relevance = doc.get("score", 0.5)  # 使用原始分数
                
                doc["relevance"] = relevance
                evaluated.append(doc)
                
            except Exception as e:
                logger.error(f"[CRAG] 文档{i}相关性评估失败: {e}")
                doc["relevance"] = doc.get("score", 0.5)
                evaluated.append(doc)
        
        logger.info(f"[CRAG] 相关性评估完成")
        return evaluated
    
    def _refine_knowledge(self, text: str) -> str:
        """
        精炼知识，提取关键信息
        
        Args:
            text: 原始文本
            
        Returns:
            精炼后的文本
        """
        try:
            system_prompt = """请从文本中提取关键信息，以清晰简洁的要点形式呈现。
重点关注最相关和最重要的事实与细节。
用项目符号列表格式（• 开头），每一项简洁明了。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"要提炼的文本:\n\n{text}"}
            ]
            
            refined = call_llm(
                messages=messages,
                temperature=0.3
            )
            
            logger.debug(f"[CRAG] 知识精炼完成")
            return refined.strip()
            
        except Exception as e:
            logger.error(f"[CRAG] 知识精炼失败: {e}")
            return text
    
    def _rewrite_query(self, query: str) -> str:
        """
        重写查询以提升检索效果
        
        Args:
            query: 原始查询
            
        Returns:
            重写后的查询
        """
        try:
            system_prompt = """你是查询重写专家。
请将查询重写为更适合搜索的形式：
- 使用关键词和事实性表达
- 去除不必要的词语
- 保持语义完整性
- 使查询更简洁明确

只返回重写后的查询，不要有任何解释。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"原始查询: {query}\n\n重写后的查询:"}
            ]
            
            rewritten = call_llm(
                messages=messages,
                temperature=0.3,
                max_tokens=100
            )
            
            return rewritten.strip()
            
        except Exception as e:
            logger.error(f"[CRAG] 查询重写失败: {e}")
            return query
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于纠错后的文档生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 检索到的文档
            
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
            
            logger.info(f"[CRAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[CRAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

