from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import call_llm, generate_rag_answer


class AdaptiveRAG(BaseRAG):
    """Adaptive RAG - 自适应RAG
    
    根据查询类型自动选择最佳检索策略：
    1. Factual (事实性) - 精确检索
    2. Analytical (分析性) - 全面覆盖
    3. Opinion (观点性) - 多元视角  
    4. Contextual (上下文型) - 情境整合
    
    流程：
    1. 分类查询类型
    2. 选择对应的检索策略
    3. 执行检索
    4. 生成答案
    
    优势：
    - 智能路由，自动优化
    - 适应不同类型问题
    - 提升整体效果
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Adaptive RAG", vector_store, config)
        self.system_prompt = config.get("system_prompt") if config else None
    
    def _classify_query(self, query: str) -> str:
        """
        将查询分类为四个类别之一
        
        Args:
            query: 用户查询
            
        Returns:
            查询类别: Factual/Analytical/Opinion/Contextual
        """
        try:
            system_prompt = """你是专业的查询分类专家。
请将给定查询严格分类至以下四类中的唯一一项：
- Factual：需要具体、可验证信息的查询（如"什么是"、"如何定义"）
- Analytical：需要综合分析或深入解释的查询（如"为什么"、"如何影响"）
- Opinion：涉及主观问题或寻求多元观点的查询（如"怎么看"、"优缺点"）
- Contextual：依赖用户具体情境的查询（如"适合我"、"如何应用"）

请仅返回分类名称，不要添加任何解释。"""
            
            user_prompt = f"对以下查询进行分类: {query}"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            category = call_llm(messages=messages, temperature=0, max_tokens=50).strip()
            
            # 确保返回有效类别
            valid_categories = ["Factual", "Analytical", "Opinion", "Contextual"]
            for valid in valid_categories:
                if valid in category:
                    logger.info(f"[Adaptive RAG] 查询分类: {valid}")
                    return valid
            
            # 默认返回Factual
            logger.warning(f"[Adaptive RAG] 分类失败，默认使用Factual")
            return "Factual"
            
        except Exception as e:
            logger.error(f"[Adaptive RAG] 查询分类失败: {e}")
            return "Factual"
    
    def _factual_retrieval(self, query: str, top_k: int) -> List[Dict]:
        """事实性检索策略 - 精确导向"""
        try:
            # 优化查询
            system_prompt = "你是搜索查询优化专家。请重构查询使其更精确具体，重点关注关键实体。只返回优化后的查询。"
            enhanced_query = call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"优化此查询: {query}"}
                ],
                temperature=0,
                max_tokens=200
            ).strip()
            
            logger.info(f"[Adaptive RAG-Factual] 优化查询: {query} → {enhanced_query}")
            
            # 使用优化后的查询检索
            results = self.vector_store.similarity_search(
                query=enhanced_query,
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[Adaptive RAG-Factual] 检索失败: {e}")
            # 回退到原查询
            return self.vector_store.similarity_search(query=query, top_k=top_k)
    
    def _analytical_retrieval(self, query: str, top_k: int) -> List[Dict]:
        """分析性检索策略 - 全面覆盖"""
        try:
            # 生成子问题
            system_prompt = "你是复杂问题拆解专家。生成3个子问题探索不同维度，每个问题单独一行。"
            sub_queries_text = call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"为此查询生成子问题: {query}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            sub_queries = [q.strip() for q in sub_queries_text.split('\n') if q.strip()][:3]
            logger.info(f"[Adaptive RAG-Analytical] 生成 {len(sub_queries)} 个子问题")
            
            # 为每个子问题检索
            all_results = []
            seen_chunks = set()
            
            for sq in sub_queries:
                results = self.vector_store.similarity_search(query=sq, top_k=2)
                for r in results:
                    if r["chunk_id"] not in seen_chunks:
                        seen_chunks.add(r["chunk_id"])
                        all_results.append(r)
            
            # 如果结果不足，补充主查询结果
            if len(all_results) < top_k:
                main_results = self.vector_store.similarity_search(query=query, top_k=top_k)
                for r in main_results:
                    if r["chunk_id"] not in seen_chunks and len(all_results) < top_k:
                        seen_chunks.add(r["chunk_id"])
                        all_results.append(r)
            
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"[Adaptive RAG-Analytical] 检索失败: {e}")
            return self.vector_store.similarity_search(query=query, top_k=top_k)
    
    def _opinion_retrieval(self, query: str, top_k: int) -> List[Dict]:
        """观点性检索策略 - 多元视角"""
        try:
            # 识别不同观点
            system_prompt = "你是主题多视角分析专家。识别3个不同观点角度，每个角度单独一行。"
            viewpoints_text = call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"识别此主题的不同观点: {query}"}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            viewpoints = [v.strip() for v in viewpoints_text.split('\n') if v.strip()][:3]
            logger.info(f"[Adaptive RAG-Opinion] 识别 {len(viewpoints)} 个观点")
            
            # 为每个观点检索
            all_results = []
            seen_chunks = set()
            
            for vp in viewpoints:
                combined_query = f"{query} {vp}"
                results = self.vector_store.similarity_search(query=combined_query, top_k=2)
                for r in results:
                    if r["chunk_id"] not in seen_chunks:
                        seen_chunks.add(r["chunk_id"])
                        r["viewpoint"] = vp
                        all_results.append(r)
            
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"[Adaptive RAG-Opinion] 检索失败: {e}")
            return self.vector_store.similarity_search(query=query, top_k=top_k)
    
    def _contextual_retrieval(self, query: str, top_k: int) -> List[Dict]:
        """上下文型检索策略 - 情境整合"""
        try:
            # 推断隐含上下文
            system_prompt = "你是理解查询隐含上下文的专家。简要描述推断的背景信息。"
            context = call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"推断此查询的隐含背景: {query}"}
                ],
                temperature=0.1,
                max_tokens=200
            ).strip()
            
            logger.info(f"[Adaptive RAG-Contextual] 推断上下文: {context[:100]}")
            
            # 结合上下文重构查询
            system_prompt = "你是上下文整合专家。结合上下文重构查询。只返回重构后的查询。"
            contextualized_query = call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"查询: {query}\n上下文: {context}\n重构查询:"}
                ],
                temperature=0,
                max_tokens=200
            ).strip()
            
            logger.info(f"[Adaptive RAG-Contextual] 重构查询: {contextualized_query}")
            
            # 使用重构后的查询检索
            results = self.vector_store.similarity_search(
                query=contextualized_query,
                top_k=top_k
            )
            
            return results
            
        except Exception as e:
            logger.error(f"[Adaptive RAG-Contextual] 检索失败: {e}")
            return self.vector_store.similarity_search(query=query, top_k=top_k)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        自适应检索
        
        Args:
            query: 用户查询
            top_k: 返回文档数
            
        Returns:
            检索到的文档列表
        """
        try:
            # Step 1: 分类查询
            category = self._classify_query(query)
            
            # Step 2: 根据类别选择策略
            if category == "Factual":
                results = self._factual_retrieval(query, top_k)
            elif category == "Analytical":
                results = self._analytical_retrieval(query, top_k)
            elif category == "Opinion":
                results = self._opinion_retrieval(query, top_k)
            elif category == "Contextual":
                results = self._contextual_retrieval(query, top_k)
            else:
                results = self.vector_store.similarity_search(query=query, top_k=top_k)
            
            # Step 3: 转换为RetrievedDoc
            retrieved_docs = []
            for result in results:
                doc = RetrievedDoc(
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    score=result["score"],
                    metadata={
                        "doc_id": result.get("doc_id", ""),
                        "filename": result.get("filename", ""),
                        "chunk_index": result.get("chunk_index", 0),
                        "query_category": category,
                        "viewpoint": result.get("viewpoint", ""),
                    }
                )
                retrieved_docs.append(doc)
            
            logger.info(f"[Adaptive RAG] 检索完成，类别: {category}，返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Adaptive RAG] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """生成答案"""
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            context = [doc.content for doc in retrieved_docs]
            
            # 获取查询类别
            category = retrieved_docs[0].metadata.get("query_category", "")
            
            # 根据类别调整系统提示
            if category == "Analytical":
                system_prompt = "你是专业的分析助手。请基于文档提供全面深入的分析，覆盖多个维度。"
            elif category == "Opinion":
                system_prompt = "你是客观的观点总结助手。请平衡呈现文档中的不同观点和立场。"
            elif category == "Contextual":
                system_prompt = "你是情境化问答助手。请结合具体上下文提供针对性的回答。"
            else:  # Factual
                system_prompt = "你是准确的事实问答助手。请基于文档提供准确具体的信息。"
            
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=system_prompt
            )
            
            logger.info(f"[Adaptive RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Adaptive RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

