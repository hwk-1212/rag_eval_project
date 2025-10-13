from typing import List, Dict, Any, Optional
from loguru import logger
import re
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import call_llm, generate_rag_answer


class QueryTransformationRAG(BaseRAG):
    """Query Transformation RAG - 查询转换优化
    
    实现三种查询转换技术：
    1. Query Rewriting - 查询重写：使查询更具体和详细
    2. Step-back Prompting - 回退提示：生成更广泛的背景查询
    3. Sub-query Decomposition - 子查询分解：将复杂查询拆分
    
    流程：
    1. 根据配置选择转换策略
    2. 转换原始查询
    3. 使用转换后的查询检索
    4. 融合多个查询的结果（如果有）
    5. 生成最终答案
    
    优势：
    - 改善复杂查询的检索效果
    - 多角度检索提高召回率
    - 适应不同类型的问题
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Query Transformation RAG", vector_store, config)
        self.transformation_type = config.get("transformation_type", "rewrite") if config else "rewrite"
        self.num_subqueries = config.get("num_subqueries", 3) if config else 3
        self.system_prompt = config.get("system_prompt") if config else None
    
    def _rewrite_query(self, original_query: str) -> str:
        """
        查询重写：使查询更具体和详细
        
        Args:
            original_query: 原始查询
            
        Returns:
            重写后的查询
        """
        try:
            system_prompt = "你是一个专注于优化搜索查询的AI助手。你的任务是通过重写用户查询，使其更加具体、详细，并提升检索相关信息的有效性。"
            
            user_prompt = f"""请优化以下搜索查询，使其满足：
1. 增强查询的具体性和详细程度
2. 包含有助于获取准确信息的相关术语和核心概念
3. 保持简洁，不要过于冗长

原始查询：{original_query}

请直接输出优化后的查询，不要额外解释："""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            rewritten = call_llm(messages=messages, temperature=0.0, max_tokens=200)
            
            # 清理结果
            rewritten = rewritten.strip()
            if "优化后的查询" in rewritten:
                rewritten = rewritten.split("优化后的查询")[-1].strip(": \n")
            
            logger.info(f"[Query Transform] 查询重写: {original_query} → {rewritten}")
            return rewritten
            
        except Exception as e:
            logger.error(f"[Query Transform] 查询重写失败: {e}")
            return original_query
    
    def _generate_stepback_query(self, original_query: str) -> str:
        """
        回退提示：生成更广泛的背景查询
        
        Args:
            original_query: 原始查询
            
        Returns:
            回退查询
        """
        try:
            system_prompt = "你是一个专注于搜索策略的AI助手。你的任务是将具体查询转化为更宽泛、更通用的版本，以帮助检索相关背景信息。"
            
            user_prompt = f"""请基于以下具体查询生成一个更通用的版本，要求：
1. 扩大查询范围以涵盖背景信息
2. 包含潜在相关领域的关键概念
3. 保持语义完整性

原始查询: {original_query}

请直接输出通用化查询，不要额外解释："""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            stepback = call_llm(messages=messages, temperature=0.1, max_tokens=200)
            stepback = stepback.strip()
            
            logger.info(f"[Query Transform] 回退查询: {original_query} → {stepback}")
            return stepback
            
        except Exception as e:
            logger.error(f"[Query Transform] 回退查询失败: {e}")
            return original_query
    
    def _decompose_query(self, original_query: str) -> List[str]:
        """
        子查询分解：将复杂查询拆分为简单子查询
        
        Args:
            original_query: 原始查询
            
        Returns:
            子查询列表
        """
        try:
            system_prompt = "你是一个专门负责分解复杂问题的AI助手。你的任务是将复杂的查询拆解成更简单的子问题。"
            
            user_prompt = f"""将以下复杂查询分解为{self.num_subqueries}个更简单的子问题。每个子问题应聚焦原始问题的不同方面。

原始查询: {original_query}

请生成{self.num_subqueries}个子问题，每个问题单独一行，按以下格式：
1. [第一个子问题]
2. [第二个子问题]
3. [第三个子问题]
依此类推..."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = call_llm(messages=messages, temperature=0.2, max_tokens=500)
            
            # 解析子查询
            pattern = r'^\d+\.\s*(.*)'
            sub_queries = []
            for line in response.split('\n'):
                line = line.strip()
                match = re.match(pattern, line)
                if match:
                    sub_queries.append(match.group(1).strip())
            
            if not sub_queries:
                logger.warning("[Query Transform] 子查询解析失败，使用原查询")
                return [original_query]
            
            logger.info(f"[Query Transform] 查询分解: {len(sub_queries)}个子查询")
            for i, sq in enumerate(sub_queries, 1):
                logger.debug(f"  {i}. {sq}")
            
            return sub_queries
            
        except Exception as e:
            logger.error(f"[Query Transform] 查询分解失败: {e}")
            return [original_query]
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        使用查询转换进行检索
        
        Args:
            query: 原始查询
            top_k: 返回文档数
            
        Returns:
            检索到的文档列表
        """
        try:
            transformed_queries = []
            
            # 根据策略转换查询
            if self.transformation_type == "rewrite":
                transformed_queries = [self._rewrite_query(query)]
                
            elif self.transformation_type == "stepback":
                transformed_queries = [self._generate_stepback_query(query)]
                
            elif self.transformation_type == "decompose":
                transformed_queries = self._decompose_query(query)
                
            elif self.transformation_type == "hybrid":
                # 混合策略：重写+分解
                rewritten = self._rewrite_query(query)
                transformed_queries = [rewritten] + self._decompose_query(query)[:2]
            
            else:
                transformed_queries = [query]
            
            # 对每个转换后的查询进行检索
            all_results = {}
            for tq in transformed_queries:
                results = self.vector_store.similarity_search(
                    query=tq,
                    top_k=top_k * 2  # 获取更多候选
                )
                
                # 合并结果，去重
                for result in results:
                    chunk_id = result["chunk_id"]
                    if chunk_id not in all_results:
                        all_results[chunk_id] = result
                    else:
                        # 保留更高的分数
                        if result["score"] > all_results[chunk_id]["score"]:
                            all_results[chunk_id] = result
            
            # 按分数排序并取top_k
            sorted_results = sorted(
                all_results.values(),
                key=lambda x: x["score"],
                reverse=True
            )[:top_k]
            
            # 转换为RetrievedDoc
            retrieved_docs = []
            for result in sorted_results:
                doc = RetrievedDoc(
                    chunk_id=result["chunk_id"],
                    content=result["content"],
                    score=result["score"],
                    metadata={
                        "doc_id": result.get("doc_id", ""),
                        "filename": result.get("filename", ""),
                        "chunk_index": result.get("chunk_index", 0),
                        "transformation_type": self.transformation_type,
                        "num_queries": len(transformed_queries),
                    }
                )
                retrieved_docs.append(doc)
            
            logger.info(f"[Query Transform] 检索完成，返回 {len(retrieved_docs)} 个文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Query Transform] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """生成答案"""
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            context = [doc.content for doc in retrieved_docs]
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[Query Transform] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Query Transform] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

