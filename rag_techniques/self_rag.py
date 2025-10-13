from typing import List, Dict, Any, Optional
from loguru import logger
import re
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import call_llm, generate_rag_answer


class SelfRAG(BaseRAG):
    """Self RAG - 自我反思RAG
    
    通过多个反思点动态控制检索和生成过程：
    1. 检索决策 - 判断是否需要检索
    2. 相关性评估 - 评估检索文档的相关性
    3. 支持性评估 - 验证答案是否基于文档
    4. 效用评估 - 评估答案的实用性
    5. 选择最佳答案
    
    流程：
    1. 判断查询是否需要检索
    2. 如果需要，检索并评估相关性
    3. 对每个相关文档生成答案
    4. 评估答案的支持性和效用
    5. 选择最佳答案
    
    优势：
    - 避免不必要的检索
    - 确保答案质量
    - 多重质量检验
    - 自适应决策
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Self RAG", vector_store, config)
        self.system_prompt = config.get("system_prompt") if config else None
        self.min_support_score = config.get("min_support_score", 1) if config else 1
    
    def _determine_retrieval_needed(self, query: str) -> bool:
        """
        判断查询是否需要检索
        
        Args:
            query: 用户查询
            
        Returns:
            True if需要检索, False otherwise
        """
        try:
            system_prompt = """你是一个判断查询是否需要检索的AI助手。
针对事实性问题、具体信息请求或关于事件、人物、概念的查询，回答"Yes"。
对于观点类、假设性场景或常识性简单查询，回答"No"。
仅回答"Yes"或"No"。"""
            
            user_prompt = f"查询: {query}\n\n此查询是否需要检索文档？"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            answer = call_llm(messages=messages, temperature=0, max_tokens=10).strip().lower()
            
            need_retrieval = "yes" in answer
            logger.info(f"[Self RAG] 检索决策: {need_retrieval}")
            return need_retrieval
            
        except Exception as e:
            logger.error(f"[Self RAG] 检索决策失败: {e}")
            return True  # 默认需要检索
    
    def _evaluate_relevance(self, query: str, context: str) -> bool:
        """
        评估文档与查询的相关性
        
        Args:
            query: 查询
            context: 文档内容
            
        Returns:
            True if相关, False otherwise
        """
        try:
            system_prompt = """你是一个AI助手，任务是判断文档是否与查询相关。
判断文档中是否包含有助于回答查询的信息。
仅回答"Relevant"或"Irrelevant"。"""
            
            # 限制上下文长度
            max_length = 1500
            if len(context) > max_length:
                context = context[:max_length] + "..."
            
            user_prompt = f"""查询: {query}

文档内容:
{context}

该文档与查询相关？仅回答"Relevant"或"Irrelevant"。"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            answer = call_llm(messages=messages, temperature=0, max_tokens=20).strip().lower()
            
            is_relevant = "relevant" in answer
            return is_relevant
            
        except Exception as e:
            logger.error(f"[Self RAG] 相关性评估失败: {e}")
            return True  # 默认相关
    
    def _assess_support(self, response: str, context: str) -> str:
        """
        评估响应是否得到上下文支持
        
        Args:
            response: 生成的响应
            context: 上下文内容
            
        Returns:
            支持等级: "fully"/"partially"/"none"
        """
        try:
            system_prompt = """你是一个AI助手，任务是判断回答是否基于给定的上下文。
评估响应中的事实、主张和信息是否由上下文支持。
仅回答以下三个选项之一：
- "Fully supported"：回答所有信息均可从上下文直接得出
- "Partially supported"：回答中的部分信息由上下文支持
- "No support"：回答中包含未在上下文中找到的信息"""
            
            # 限制上下文长度
            max_length = 1500
            if len(context) > max_length:
                context = context[:max_length] + "..."
            
            user_prompt = f"""上下文:
{context}

回答:
{response}

该回答与上下文的支持程度如何？"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            answer = call_llm(messages=messages, temperature=0, max_tokens=50).strip().lower()
            
            if "fully" in answer:
                return "fully"
            elif "partially" in answer:
                return "partially"
            else:
                return "none"
                
        except Exception as e:
            logger.error(f"[Self RAG] 支持性评估失败: {e}")
            return "partially"
    
    def _rate_utility(self, query: str, response: str) -> int:
        """
        评估响应的实用性
        
        Args:
            query: 查询
            response: 响应
            
        Returns:
            实用性评分 1-5
        """
        try:
            system_prompt = """你是一个AI助手，任务是评估一个回答对查询的实用性。
从回答准确性、完整性、正确性和帮助性进行综合评分。
使用1-5级评分标准：
- 1：毫无用处
- 2：稍微有用
- 3：中等有用
- 4：非常有用
- 5：极其有用
仅回答一个从1到5的单个数字。"""
            
            user_prompt = f"""查询: {query}

回答:
{response}

请用1到5分评估该回答的实用性："""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            rating_text = call_llm(messages=messages, temperature=0, max_tokens=10).strip()
            
            # 提取数字
            match = re.search(r'[1-5]', rating_text)
            if match:
                return int(match.group())
            return 3  # 默认中等
            
        except Exception as e:
            logger.error(f"[Self RAG] 效用评估失败: {e}")
            return 3
    
    def _generate_response(self, query: str, context: Optional[str] = None) -> str:
        """
        生成响应
        
        Args:
            query: 查询
            context: 可选的上下文
            
        Returns:
            生成的响应
        """
        try:
            system_prompt = "你是一个有帮助的AI助手。请针对查询提供清晰、准确且信息丰富的回答。"
            
            if context:
                user_prompt = f"""参考以下上下文回答问题：

上下文:
{context}

问题: {query}

请基于提供的上下文回答该问题。"""
            else:
                user_prompt = f"问题: {query}\n\n请尽你所能回答该问题。"
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = call_llm(messages=messages, temperature=0.2, max_tokens=1000)
            return response.strip()
            
        except Exception as e:
            logger.error(f"[Self RAG] 生成响应失败: {e}")
            return ""
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        Self-RAG检索流程
        
        Args:
            query: 用户查询
            top_k: 返回文档数
            
        Returns:
            检索到的文档列表
        """
        try:
            # Step 1: 判断是否需要检索
            need_retrieval = self._determine_retrieval_needed(query)
            
            if not need_retrieval:
                logger.info("[Self RAG] 不需要检索，将直接生成答案")
                return []
            
            # Step 2: 检索文档
            logger.info("[Self RAG] 开始检索文档")
            results = self.vector_store.similarity_search(
                query=query,
                top_k=top_k * 2  # 检索更多候选
            )
            
            # Step 3: 评估相关性
            relevant_docs = []
            for result in results:
                is_relevant = self._evaluate_relevance(query, result["content"])
                if is_relevant:
                    doc = RetrievedDoc(
                        chunk_id=result["chunk_id"],
                        content=result["content"],
                        score=result["score"],
                        metadata={
                            "doc_id": result.get("doc_id", ""),
                            "filename": result.get("filename", ""),
                            "chunk_index": result.get("chunk_index", 0),
                            "is_relevant": True,
                        }
                    )
                    relevant_docs.append(doc)
            
            logger.info(f"[Self RAG] 检索到 {len(results)} 个文档，相关文档 {len(relevant_docs)} 个")
            return relevant_docs[:top_k]
            
        except Exception as e:
            logger.error(f"[Self RAG] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        Self-RAG生成流程
        
        Args:
            query: 查询
            retrieved_docs: 检索到的文档
            
        Returns:
            最佳答案
        """
        try:
            # 如果没有检索文档，直接生成答案
            if not retrieved_docs:
                logger.info("[Self RAG] 无检索文档，直接生成答案")
                return self._generate_response(query)
            
            # Step 4: 对每个相关文档生成答案并评估
            best_response = None
            best_score = -1
            
            logger.info(f"[Self RAG] 开始评估 {len(retrieved_docs)} 个候选答案")
            
            for i, doc in enumerate(retrieved_docs[:3], 1):  # 最多评估3个
                # 生成响应
                response = self._generate_response(query, doc.content)
                
                # 评估支持性
                support_level = self._assess_support(response, doc.content)
                support_score = {"fully": 3, "partially": 1, "none": 0}.get(support_level, 0)
                
                # 评估效用
                utility_score = self._rate_utility(query, response)
                
                # 计算总分
                overall_score = support_score * 5 + utility_score
                
                logger.info(f"[Self RAG] 候选{i}: 支持={support_level}, 效用={utility_score}/5, 总分={overall_score}")
                
                # 更新最佳答案
                if overall_score > best_score:
                    best_response = response
                    best_score = overall_score
            
            # 如果所有答案评分都很低，直接生成
            if best_score < self.min_support_score:
                logger.warning(f"[Self RAG] 所有答案评分过低（{best_score}），直接生成答案")
                return self._generate_response(query)
            
            logger.info(f"[Self RAG] 选择最佳答案，评分: {best_score}")
            return best_response
            
        except Exception as e:
            logger.error(f"[Self RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

