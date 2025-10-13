"""
Ragas框架评估包装器
使用Ragas进行标准化RAG评估
"""
from typing import List, Dict, Any, Optional
from loguru import logger
import traceback

try:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        faithfulness,
        answer_relevancy,
        context_recall,
        context_precision,
        answer_similarity,
        answer_correctness
    )
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    logger.warning("[RagasEvaluator] Ragas未安装，相关功能将不可用")


class RagasEvaluator:
    """
    Ragas评估器
    使用Ragas框架进行标准化评估
    """
    
    def __init__(self):
        """初始化Ragas评估器"""
        if not RAGAS_AVAILABLE:
            logger.error("[RagasEvaluator] Ragas未安装，请运行: pip install ragas")
            self.available = False
        else:
            self.available = True
            logger.info("[RagasEvaluator] 初始化完成")
    
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
            
            # 执行评估
            result = evaluate(
                dataset,
                metrics=metrics,
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
            
            # 执行评估
            result = evaluate(dataset, metrics=metrics)
            
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

