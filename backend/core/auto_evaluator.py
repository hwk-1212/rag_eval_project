"""
自动化评估模块
结合LLM评分和Ragas框架进行多维度RAG评估
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import re
import json
from openai import OpenAI


class AutoEvaluator:
    """自动化评估器"""
    
    def __init__(
        self,
        llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        llm_api_key: str = "sk-e96412163b6a4f6189b65b98532eaf77",
        llm_model: str = "qwen-plus"
    ):
        """
        初始化评估器
        
        Args:
            llm_base_url: 评分模型的API地址
            llm_api_key: API密钥
            llm_model: 评分使用的模型
        """
        self.client = OpenAI(
            base_url=llm_base_url,
            api_key=llm_api_key
        )
        self.model = llm_model
        logger.info(f"[AutoEvaluator] 初始化完成，使用模型: {llm_model}")
    
    def evaluate_answer(
        self,
        query: str,
        answer: str,
        retrieved_contexts: List[str],
        reference_answer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        全面评估RAG答案质量
        
        Args:
            query: 用户查询
            answer: RAG生成的答案
            retrieved_contexts: 检索到的上下文列表
            reference_answer: 参考答案（可选）
            
        Returns:
            评估结果字典
        """
        logger.info("[AutoEvaluator] 开始评估答案...")
        
        results = {
            # LLM评分指标
            "relevance_score": 0.0,        # 相关性
            "faithfulness_score": 0.0,     # 忠实度
            "coherence_score": 0.0,        # 连贯性
            "fluency_score": 0.0,          # 流畅度
            "conciseness_score": 0.0,      # 简洁性
            
            # 综合评分
            "overall_score": 0.0,
            
            # 详细反馈
            "feedback": "",
            
            # 评估状态
            "evaluation_success": True,
            "error_message": None
        }
        
        try:
            # 1. 相关性评估
            results["relevance_score"] = self._evaluate_relevance(query, answer)
            
            # 2. 忠实度评估（答案是否基于检索内容）
            results["faithfulness_score"] = self._evaluate_faithfulness(
                answer, retrieved_contexts
            )
            
            # 3. 连贯性评估
            results["coherence_score"] = self._evaluate_coherence(answer)
            
            # 4. 流畅度评估
            results["fluency_score"] = self._evaluate_fluency(answer)
            
            # 5. 简洁性评估
            results["conciseness_score"] = self._evaluate_conciseness(answer)
            
            # 6. 如果有参考答案，评估正确性
            if reference_answer:
                results["correctness_score"] = self._evaluate_correctness(
                    answer, reference_answer
                )
            
            # 7. 计算综合评分
            scores = [
                results["relevance_score"],
                results["faithfulness_score"],
                results["coherence_score"],
                results["fluency_score"],
                results["conciseness_score"]
            ]
            results["overall_score"] = round(sum(scores) / len(scores), 2)
            
            # 8. 生成反馈
            results["feedback"] = self._generate_feedback(results)
            
            logger.info(f"[AutoEvaluator] 评估完成，综合得分: {results['overall_score']}")
            
        except Exception as e:
            logger.error(f"[AutoEvaluator] 评估失败: {e}")
            results["evaluation_success"] = False
            results["error_message"] = str(e)
        
        return results
    
    def _evaluate_relevance(self, query: str, answer: str) -> float:
        """
        评估答案与查询的相关性
        
        Args:
            query: 查询
            answer: 答案
            
        Returns:
            相关性分数 (0-10)
        """
        try:
            system_prompt = """你是专业的答案质量评估专家。请评估答案与问题的相关性。

评分标准（0-10分）：
- 10分：完美回答问题，完全相关
- 7-9分：回答了问题的主要部分，高度相关
- 4-6分：部分回答了问题，中等相关
- 1-3分：基本没有回答问题，弱相关
- 0分：完全无关

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""问题：{query}

答案：{answer}

相关性评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Relevance] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Relevance] 评估失败: {e}")
            return 5.0
    
    def _evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        评估答案的忠实度（是否基于检索内容）
        
        Args:
            answer: 答案
            contexts: 检索到的上下文
            
        Returns:
            忠实度分数 (0-10)
        """
        try:
            # 合并上下文
            combined_context = "\n\n".join(contexts[:3])  # 只用前3个
            
            # 限制长度
            if len(combined_context) > 2000:
                combined_context = combined_context[:2000] + "..."
            
            system_prompt = """你是专业的答案忠实度评估专家。请评估答案是否基于提供的上下文。

评分标准（0-10分）：
- 10分：答案完全基于上下文，没有任何额外信息
- 7-9分：答案主要基于上下文，有少量合理推断
- 4-6分：答案部分基于上下文，部分来自外部知识
- 1-3分：答案大部分不基于上下文
- 0分：答案完全不基于上下文或与上下文矛盾

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""上下文：
{combined_context}

答案：{answer}

忠实度评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Faithfulness] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Faithfulness] 评估失败: {e}")
            return 5.0
    
    def _evaluate_coherence(self, answer: str) -> float:
        """
        评估答案的连贯性
        
        Args:
            answer: 答案
            
        Returns:
            连贯性分数 (0-10)
        """
        try:
            system_prompt = """你是专业的文本连贯性评估专家。请评估答案的逻辑连贯性和结构性。

评分标准（0-10分）：
- 10分：逻辑非常清晰，结构完美，前后一致
- 7-9分：逻辑清晰，结构良好，基本一致
- 4-6分：逻辑基本清晰，结构一般
- 1-3分：逻辑混乱，结构不清
- 0分：完全不连贯

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""答案：{answer}

连贯性评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Coherence] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Coherence] 评估失败: {e}")
            return 5.0
    
    def _evaluate_fluency(self, answer: str) -> float:
        """
        评估答案的流畅度
        
        Args:
            answer: 答案
            
        Returns:
            流畅度分数 (0-10)
        """
        try:
            system_prompt = """你是专业的文本流畅度评估专家。请评估答案的语言流畅度和可读性。

评分标准（0-10分）：
- 10分：语言非常流畅，阅读体验极佳
- 7-9分：语言流畅，易于阅读
- 4-6分：语言基本流畅，有少量瑕疵
- 1-3分：语言不够流畅，阅读困难
- 0分：语言混乱，无法阅读

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""答案：{answer}

流畅度评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Fluency] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Fluency] 评估失败: {e}")
            return 5.0
    
    def _evaluate_conciseness(self, answer: str) -> float:
        """
        评估答案的简洁性
        
        Args:
            answer: 答案
            
        Returns:
            简洁性分数 (0-10)
        """
        try:
            system_prompt = """你是专业的文本简洁性评估专家。请评估答案是否简洁明了，没有冗余。

评分标准（0-10分）：
- 10分：非常简洁，没有任何冗余
- 7-9分：比较简洁，少量冗余
- 4-6分：基本简洁，有一定冗余
- 1-3分：冗余较多，不够简洁
- 0分：极度冗长，大量冗余

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""答案：{answer}

简洁性评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Conciseness] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Conciseness] 评估失败: {e}")
            return 5.0
    
    def _evaluate_correctness(self, answer: str, reference: str) -> float:
        """
        评估答案的正确性（与参考答案对比）
        
        Args:
            answer: 答案
            reference: 参考答案
            
        Returns:
            正确性分数 (0-10)
        """
        try:
            system_prompt = """你是专业的答案正确性评估专家。请对比答案和参考答案，评估正确性。

评分标准（0-10分）：
- 10分：与参考答案完全一致或更优
- 7-9分：与参考答案基本一致，少量差异
- 4-6分：部分正确，有一定差异
- 1-3分：大部分不正确
- 0分：完全错误

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""参考答案：{reference}

待评估答案：{answer}

正确性评分（0-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            logger.debug(f"[Correctness] 分数: {score}")
            return score
            
        except Exception as e:
            logger.error(f"[Correctness] 评估失败: {e}")
            return 5.0
    
    def _call_llm_for_score(self, system_prompt: str, user_prompt: str) -> float:
        """
        调用LLM获取评分
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            
        Returns:
            评分 (0-10)
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            score_text = response.choices[0].message.content.strip()
            
            # 提取数字
            match = re.search(r'(\d+(\.\d+)?)', score_text)
            if match:
                score = float(match.group(1))
                return min(10.0, max(0.0, score))  # 确保在0-10范围内
            else:
                logger.warning(f"[LLM Score] 无法提取分数: {score_text}")
                return 5.0
                
        except Exception as e:
            logger.error(f"[LLM Score] 调用失败: {e}")
            return 5.0
    
    def _generate_feedback(self, results: Dict[str, Any]) -> str:
        """
        根据评分结果生成反馈
        
        Args:
            results: 评分结果
            
        Returns:
            反馈文本
        """
        feedback_parts = []
        
        # 整体评价
        overall = results["overall_score"]
        if overall >= 8:
            feedback_parts.append("✅ 整体表现优秀")
        elif overall >= 6:
            feedback_parts.append("👍 整体表现良好")
        elif overall >= 4:
            feedback_parts.append("⚠️ 整体表现一般")
        else:
            feedback_parts.append("❌ 整体表现较差")
        
        # 各项具体评价
        metrics = {
            "relevance_score": "相关性",
            "faithfulness_score": "忠实度",
            "coherence_score": "连贯性",
            "fluency_score": "流畅度",
            "conciseness_score": "简洁性"
        }
        
        strengths = []
        weaknesses = []
        
        for key, name in metrics.items():
            score = results.get(key, 0)
            if score >= 8:
                strengths.append(f"{name}优秀({score:.1f})")
            elif score < 5:
                weaknesses.append(f"{name}较弱({score:.1f})")
        
        if strengths:
            feedback_parts.append(f"优势：{', '.join(strengths)}")
        if weaknesses:
            feedback_parts.append(f"需改进：{', '.join(weaknesses)}")
        
        return " | ".join(feedback_parts)
    
    def evaluate_retrieval(
        self,
        query: str,
        retrieved_contexts: List[str],
        context_scores: List[float]
    ) -> Dict[str, Any]:
        """
        评估检索质量
        
        Args:
            query: 查询
            retrieved_contexts: 检索到的上下文
            context_scores: 相似度分数
            
        Returns:
            检索评估结果
        """
        logger.info("[AutoEvaluator] 开始评估检索质量...")
        
        results = {
            "retrieval_precision": 0.0,    # 检索精确度
            "context_relevance": 0.0,      # 上下文相关性
            "avg_similarity": 0.0,         # 平均相似度
            "retrieval_feedback": ""
        }
        
        try:
            # 1. 平均相似度
            if context_scores:
                results["avg_similarity"] = round(
                    sum(context_scores) / len(context_scores), 3
                )
            
            # 2. 评估每个上下文的相关性
            relevance_scores = []
            for i, context in enumerate(retrieved_contexts[:3]):  # 只评估前3个
                score = self._evaluate_context_relevance(query, context)
                relevance_scores.append(score)
            
            if relevance_scores:
                results["context_relevance"] = round(
                    sum(relevance_scores) / len(relevance_scores), 2
                )
            
            # 3. 计算精确度（相关的占比）
            relevant_count = sum(1 for s in relevance_scores if s >= 6)
            results["retrieval_precision"] = round(
                relevant_count / len(relevance_scores) if relevance_scores else 0, 2
            )
            
            # 4. 生成反馈
            if results["retrieval_precision"] >= 0.8:
                results["retrieval_feedback"] = "✅ 检索质量优秀，相关文档占比高"
            elif results["retrieval_precision"] >= 0.5:
                results["retrieval_feedback"] = "👍 检索质量良好，大部分文档相关"
            else:
                results["retrieval_feedback"] = "⚠️ 检索质量一般，需优化检索策略"
            
            logger.info(f"[AutoEvaluator] 检索评估完成，精确度: {results['retrieval_precision']}")
            
        except Exception as e:
            logger.error(f"[AutoEvaluator] 检索评估失败: {e}")
        
        return results
    
    def _evaluate_context_relevance(self, query: str, context: str) -> float:
        """
        评估单个上下文与查询的相关性
        
        Args:
            query: 查询
            context: 上下文
            
        Returns:
            相关性分数 (0-10)
        """
        try:
            # 限制长度
            if len(context) > 1000:
                context = context[:1000] + "..."
            
            system_prompt = """你是文档相关性评估专家。请评估文档片段与查询的相关性。

评分标准（0-10分）：
- 10分：完美匹配，直接回答查询
- 7-9分：高度相关，包含关键信息
- 4-6分：中等相关，包含部分信息
- 1-3分：弱相关，包含少量相关信息
- 0分：完全无关

请仅返回0-10之间的单个数字。"""
            
            user_prompt = f"""查询：{query}

文档片段：{context}

相关性评分（0-10）："""
            
            return self._call_llm_for_score(system_prompt, user_prompt)
            
        except Exception as e:
            logger.error(f"[Context Relevance] 评估失败: {e}")
            return 5.0
    
    def compare_answers(
        self,
        query: str,
        answer1: str,
        answer2: str,
        technique1: str,
        technique2: str
    ) -> Dict[str, Any]:
        """
        对比两个答案的质量
        
        Args:
            query: 查询
            answer1: 答案1
            answer2: 答案2
            technique1: 技术1名称
            technique2: 技术2名称
            
        Returns:
            对比结果
        """
        logger.info(f"[AutoEvaluator] 对比答案: {technique1} vs {technique2}")
        
        try:
            system_prompt = """你是专业的答案质量对比专家。请对比两个答案的质量。

评分标准（1-10分）：
- 10分：显著优于对方
- 7-9分：明显优于对方
- 5-6分：略优于对方
- 4分：基本相当
- 1-3分：不如对方

请仅返回answer1的得分（1-10）。"""
            
            user_prompt = f"""问题：{query}

答案1（{technique1}）：
{answer1}

答案2（{technique2}）：
{answer2}

答案1的得分（1-10）："""
            
            score = self._call_llm_for_score(system_prompt, user_prompt)
            
            # 判断优劣
            if score >= 7:
                winner = technique1
                conclusion = f"{technique1} 明显优于 {technique2}"
            elif score >= 5:
                winner = technique1
                conclusion = f"{technique1} 略优于 {technique2}"
            elif score == 4:
                winner = "tie"
                conclusion = f"{technique1} 与 {technique2} 质量相当"
            else:
                winner = technique2
                conclusion = f"{technique2} 优于 {technique1}"
            
            return {
                "winner": winner,
                "score_difference": abs(score - 4),
                "conclusion": conclusion
            }
            
        except Exception as e:
            logger.error(f"[Compare Answers] 对比失败: {e}")
            return {
                "winner": "tie",
                "score_difference": 0,
                "conclusion": "对比失败"
            }


# 单例模式
_evaluator_instance = None

def get_evaluator() -> AutoEvaluator:
    """获取评估器单例"""
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = AutoEvaluator()
    return _evaluator_instance

