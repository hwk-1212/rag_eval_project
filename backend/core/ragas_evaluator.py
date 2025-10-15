"""
Ragas框架评估包装器
使用Ragas进行标准化RAG评估
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import traceback
import os

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_recall,
        context_precision,
    )
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    RAGAS_AVAILABLE = True
except ImportError as e:
    RAGAS_AVAILABLE = False
    logger.warning(f"[RagasEvaluator] Ragas相关库未安装: {e}")


class RagasEvaluator:
    """
    Ragas评估器
    使用Ragas框架进行标准化评估
    
    Ragas评估维度：
    1. faithfulness（忠实度）：答案和上下文的关系 - 答案是否基于检索到的上下文
    2. answer_relevancy（答案相关性）：答案和问题的关系 - 答案是否回答了问题
    3. context_precision（上下文精确度）：问题和上下文的关系 - 相关上下文是否排在前面
    4. context_recall（上下文召回率）：问题和上下文的关系 - 是否检索到所有相关上下文
    """
    
    def __init__(
        self,
        llm_base_url: str = None,
        llm_api_key: str = None,
        llm_model: str = "qwen-plus",
        embedding_base_url: str = None,
        embedding_api_key: str = None,
        embedding_model: str = "text-embedding-v3"
    ):
        """
        初始化Ragas评估器
        
        Args:
            llm_base_url: LLM API地址
            llm_api_key: LLM API密钥
            llm_model: LLM模型名称
            embedding_base_url: Embedding API地址
            embedding_api_key: Embedding API密钥
            embedding_model: Embedding模型名称
        """
        if not RAGAS_AVAILABLE:
            logger.error("[RagasEvaluator] Ragas未安装，请运行: pip install ragas langchain-openai")
            self.available = False
            return
        
        try:
            # 从环境变量或参数获取配置
            self.llm_base_url = llm_base_url or os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            self.llm_api_key = llm_api_key or os.getenv("OPENAI_API_KEY", "sk-e96412163b6a4f6189b65b98532eaf77")
            self.llm_model = llm_model
            
            self.embedding_base_url = embedding_base_url or self.llm_base_url
            self.embedding_api_key = embedding_api_key or self.llm_api_key
            self.embedding_model = embedding_model
            
            # 初始化LLM（用于评估）
            self.llm = ChatOpenAI(
                model=self.llm_model,
                openai_api_key=self.llm_api_key,
                openai_api_base=self.llm_base_url,
                temperature=0
            )
            
            # 初始化Embeddings（用于相似度计算）
            self.embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=self.embedding_api_key,
                openai_api_base=self.embedding_base_url
            )
            
            self.available = True
            logger.info(f"[RagasEvaluator] 初始化完成，LLM: {self.llm_model}, Embeddings: {self.embedding_model}")
            
        except Exception as e:
            logger.error(f"[RagasEvaluator] 初始化失败: {e}")
            self.available = False
    
    def evaluate_rag(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        使用Ragas评估RAG系统
        
        Args:
            question: 问题
            answer: 生成的答案
            contexts: 检索到的上下文列表
            ground_truth: 标准答案（可选）
            
        Returns:
            评估结果字典
        """
        if not self.available:
            return {
                "error": "Ragas not available",
                "ragas_available": False
            }
        
        try:
            # 准备数据
            data = {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
            }
            
            if ground_truth:
                data["ground_truth"] = [ground_truth]
            
            # 创建数据集
            dataset = Dataset.from_dict(data)
            
            # 选择评估指标（不需要ground_truth的指标）
            metrics = [
                faithfulness,          # 忠实度：答案是否基于上下文
                answer_relevancy,      # 答案相关性：答案是否回答了问题
            ]
            
            # context_precision 和 context_recall 需要 ground_truth
            # 为了不依赖标准答案，暂时只使用上面两个指标
            
            # 如果有ground_truth，添加额外指标
            # if ground_truth:
            #     metrics.extend([
            #         context_precision,     # 上下文精确度
            #         context_recall,        # 上下文召回率
            #         answer_similarity,     # 答案相似度
            #         answer_correctness,    # 答案正确性
            #     ])
            
            logger.info("[RagasEvaluator] 开始Ragas评估...")
            logger.info(f"  - 问题: {question[:50]}...")
            logger.info(f"  - 答案: {answer[:50]}...")
            logger.info(f"  - 上下文数量: {len(contexts)}")
            
            # 执行评估（传入LLM和Embeddings）
            result = evaluate(
                dataset,
                metrics=metrics,
                llm=self.llm,
                embeddings=self.embeddings,
            )
            
            # 提取分数
            scores = {
                "faithfulness": result.get("faithfulness", 0.0),
                "answer_relevancy": result.get("answer_relevancy", 0.0),
                "context_precision": result.get("context_precision", 0.0),
                "context_recall": result.get("context_recall", 0.0),
            }
            
            if ground_truth:
                scores["answer_similarity"] = result.get("answer_similarity", 0.0)
                scores["answer_correctness"] = result.get("answer_correctness", 0.0)
            
            # 计算综合分数
            avg_score = sum(scores.values()) / len(scores) if scores else 0.0
            
            logger.info(f"[RagasEvaluator] 评估完成，平均分: {avg_score:.3f}")
            
            return {
                "ragas_available": True,
                "scores": scores,
                "average_score": round(avg_score, 3),
                "evaluation_success": True
            }
            
        except Exception as e:
            logger.error(f"[RagasEvaluator] 评估失败: {e}")
            logger.error(traceback.format_exc())
            return {
                "ragas_available": True,
                "evaluation_success": False,
                "error": str(e)
            }
    
    def batch_evaluate(
        self,
        questions: List[str],
        answers: List[str],
        contexts_list: List[List[str]],
        ground_truths: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量评估
        
        Args:
            questions: 问题列表
            answers: 答案列表
            contexts_list: 上下文列表的列表
            ground_truths: 标准答案列表（可选）
            
        Returns:
            批量评估结果
        """
        if not self.available:
            return {
                "error": "Ragas not available",
                "ragas_available": False
            }
        
        try:
            # 准备数据
            data = {
                "question": questions,
                "answer": answers,
                "contexts": contexts_list,
            }
            
            if ground_truths:
                data["ground_truth"] = ground_truths
            
            # 创建数据集
            dataset = Dataset.from_dict(data)
            
            # 选择指标
            metrics = [
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            ]
            
            if ground_truths:
                metrics.extend([
                    answer_similarity,
                    answer_correctness,
                ])
            
            logger.info(f"[RagasEvaluator] 开始批量评估 {len(questions)} 个样本...")
            
            # 执行评估（传入LLM和Embeddings）
            result = evaluate(
                dataset,
                metrics=metrics,
                llm=self.llm,
                embeddings=self.embeddings
            )
            
            # 提取结果
            return {
                "ragas_available": True,
                "evaluation_success": True,
                "num_samples": len(questions),
                "scores": dict(result),
                "average_score": round(
                    sum(result.values()) / len(result), 3
                ) if result else 0.0
            }
            
        except Exception as e:
            logger.error(f"[RagasEvaluator] 批量评估失败: {e}")
            return {
                "ragas_available": True,
                "evaluation_success": False,
                "error": str(e)
            }


# 单例
_ragas_evaluator_instance = None

def get_ragas_evaluator() -> RagasEvaluator:
    """获取Ragas评估器单例"""
    global _ragas_evaluator_instance
    if _ragas_evaluator_instance is None:
        _ragas_evaluator_instance = RagasEvaluator()
    return _ragas_evaluator_instance

