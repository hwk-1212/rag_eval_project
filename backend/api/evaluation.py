from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from loguru import logger
import time
import json

from backend.models import get_db
from backend.models.db_models import Evaluation as DBEvaluation, QARecord as DBQARecord
from backend.models.schemas import (
    EvaluationCreate, EvaluationResponse, ComparisonStats,
    AutoEvaluationRequest, AutoEvaluationResponse,
    BatchEvaluationRequest, BatchEvaluationResponse
)
from backend.core.auto_evaluator import get_evaluator
from backend.core.ragas_evaluator import get_ragas_evaluator

router = APIRouter()


@router.post("/", response_model=EvaluationResponse)
async def create_evaluation(
    evaluation: EvaluationCreate,
    db: Session = Depends(get_db)
):
    """创建评分"""
    try:
        # 验证QA记录存在
        qa_record = db.query(DBQARecord).filter(DBQARecord.id == evaluation.qa_record_id).first()
        if not qa_record:
            raise HTTPException(status_code=404, detail="QA记录不存在")
        
        # 创建评分记录
        db_eval = DBEvaluation(**evaluation.dict())
        db.add(db_eval)
        db.commit()
        db.refresh(db_eval)
        
        logger.info(f"评分创建成功: QA记录ID {evaluation.qa_record_id}")
        return db_eval
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建评分失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: int,
    db: Session = Depends(get_db)
):
    """获取评分详情"""
    evaluation = db.query(DBEvaluation).filter(DBEvaluation.id == evaluation_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="评分不存在")
    return evaluation


@router.get("/qa_record/{qa_record_id}", response_model=List[EvaluationResponse])
async def get_evaluations_by_qa_record(
    qa_record_id: int,
    db: Session = Depends(get_db)
):
    """获取某个QA记录的所有评分"""
    evaluations = db.query(DBEvaluation).filter(DBEvaluation.qa_record_id == qa_record_id).all()
    return evaluations


@router.get("/stats/comparison", response_model=List[ComparisonStats])
async def get_comparison_stats(
    db: Session = Depends(get_db)
):
    """获取不同RAG技术的对比统计"""
    try:
        # 查询统计数据
        stats = db.query(
            DBQARecord.rag_technique,
            func.count(DBQARecord.id).label("total_queries"),
            func.avg(DBQARecord.execution_time).label("avg_execution_time"),
            func.avg(DBEvaluation.overall_score).label("avg_overall_score"),
            func.avg(DBEvaluation.accuracy_score).label("avg_accuracy_score"),
            func.avg(DBEvaluation.relevance_score).label("avg_relevance_score"),
        ).outerjoin(
            DBEvaluation, DBQARecord.id == DBEvaluation.qa_record_id
        ).group_by(
            DBQARecord.rag_technique
        ).all()
        
        # 格式化结果
        results = []
        for stat in stats:
            results.append(ComparisonStats(
                technique=stat.rag_technique,
                total_queries=stat.total_queries or 0,
                avg_execution_time=round(stat.avg_execution_time or 0, 3),
                avg_overall_score=round(stat.avg_overall_score or 0, 2) if stat.avg_overall_score else 0,
                avg_accuracy_score=round(stat.avg_accuracy_score or 0, 2) if stat.avg_accuracy_score else 0,
                avg_relevance_score=round(stat.avg_relevance_score or 0, 2) if stat.avg_relevance_score else 0,
            ))
        
        return results
        
    except Exception as e:
        logger.error(f"获取对比统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 自动评估API ============

@router.post("/auto", response_model=AutoEvaluationResponse)
async def auto_evaluate(
    request: AutoEvaluationRequest,
    db: Session = Depends(get_db)
):
    """自动评估QA记录"""
    start_time = time.time()
    
    try:
        # 获取QA记录
        qa_record = db.query(DBQARecord).filter(DBQARecord.id == request.qa_record_id).first()
        if not qa_record:
            raise HTTPException(status_code=404, detail="QA记录不存在")
        
        logger.info(f"[AutoEval] 开始自动评估 QA记录 {request.qa_record_id}")
        
        # 解析retrieved_docs
        retrieved_contexts = []
        context_scores = []
        try:
            if isinstance(qa_record.retrieved_docs, str):
                retrieved_docs = json.loads(qa_record.retrieved_docs)
            else:
                retrieved_docs = qa_record.retrieved_docs
                
            for doc in retrieved_docs:
                retrieved_contexts.append(doc.get("content", ""))
            context_scores = qa_record.retrieval_scores or []
        except Exception as e:
            logger.warning(f"[AutoEval] 解析retrieved_docs失败: {e}")
        
        # 初始化结果
        llm_evaluation = None
        ragas_evaluation = None
        final_scores = {}
        
        # 1. LLM评估
        if request.use_llm_evaluator:
            logger.info("[AutoEval] 使用LLM评估器...")
            evaluator = get_evaluator()
            llm_result = evaluator.evaluate_answer(
                query=qa_record.query,
                answer=qa_record.answer,
                retrieved_contexts=retrieved_contexts,
                reference_answer=request.reference_answer
            )
            llm_evaluation = llm_result
            
            # 提取分数
            final_scores.update({
                "relevance_score": llm_result.get("relevance_score", 0.0),
                "faithfulness_score": llm_result.get("faithfulness_score", 0.0),
                "coherence_score": llm_result.get("coherence_score", 0.0),
                "fluency_score": llm_result.get("fluency_score", 0.0),
                "conciseness_score": llm_result.get("conciseness_score", 0.0),
                "overall_score": llm_result.get("overall_score", 0.0),
            })
            
            # 评估检索质量
            retrieval_eval = evaluator.evaluate_retrieval(
                query=qa_record.query,
                retrieved_contexts=retrieved_contexts,
                context_scores=context_scores
            )
            final_scores.update({
                "retrieval_precision": retrieval_eval.get("retrieval_precision", 0.0),
                "context_relevance": retrieval_eval.get("context_relevance", 0.0),
            })
        
        # 2. Ragas评估
        if request.use_ragas and retrieved_contexts:
            logger.info("[AutoEval] 使用Ragas评估...")
            ragas_evaluator = get_ragas_evaluator()
            ragas_result = ragas_evaluator.evaluate_rag(
                question=qa_record.query,
                answer=qa_record.answer,
                contexts=retrieved_contexts,
                ground_truth=request.reference_answer
            )
            ragas_evaluation = ragas_result
            
            # 提取Ragas分数
            if ragas_result.get("evaluation_success"):
                ragas_scores = ragas_result.get("scores", {})
                final_scores.update({
                    "ragas_faithfulness": ragas_scores.get("faithfulness", 0.0),
                    "ragas_answer_relevancy": ragas_scores.get("answer_relevancy", 0.0),
                    "ragas_context_precision": ragas_scores.get("context_precision", 0.0),
                    "ragas_context_recall": ragas_scores.get("context_recall", 0.0),
                })
        
        # 3. 保存评估结果到数据库
        if final_scores:
            evaluation = DBEvaluation(
                qa_record_id=request.qa_record_id,
                score_type="auto",
                # LLM评分
                accuracy_score=final_scores.get("correctness_score"),
                relevance_score=final_scores.get("relevance_score"),
                faithfulness_score=final_scores.get("faithfulness_score"),
                coherence_score=final_scores.get("coherence_score"),
                fluency_score=final_scores.get("fluency_score"),
                conciseness_score=final_scores.get("conciseness_score"),
                completeness_score=final_scores.get("ragas_context_recall"),
                overall_score=final_scores.get("overall_score"),
                comments=llm_evaluation.get("feedback", "") if llm_evaluation else "",
                evaluator="AutoEvaluator"
            )
            db.add(evaluation)
            db.commit()
            logger.info(f"[AutoEval] 评估结果已保存到数据库，overall_score={final_scores.get('overall_score')}")
        
        elapsed_time = time.time() - start_time
        
        return AutoEvaluationResponse(
            qa_record_id=request.qa_record_id,
            evaluation_success=True,
            llm_evaluation=llm_evaluation,
            ragas_evaluation=ragas_evaluation,
            final_scores=final_scores,
            evaluation_time=round(elapsed_time, 2)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AutoEval] 自动评估失败: {e}")
        elapsed_time = time.time() - start_time
        return AutoEvaluationResponse(
            qa_record_id=request.qa_record_id,
            evaluation_success=False,
            llm_evaluation=None,
            ragas_evaluation=None,
            final_scores={},
            error_message=str(e),
            evaluation_time=round(elapsed_time, 2)
        )


@router.post("/auto/batch", response_model=BatchEvaluationResponse)
async def batch_auto_evaluate(
    request: BatchEvaluationRequest,
    db: Session = Depends(get_db)
):
    """批量自动评估"""
    start_time = time.time()
    
    try:
        logger.info(f"[AutoEval] 开始批量评估 {len(request.qa_record_ids)} 条记录")
        
        results = []
        success_count = 0
        failed_count = 0
        
        for qa_id in request.qa_record_ids:
            try:
                # 调用单条评估
                eval_request = AutoEvaluationRequest(
                    qa_record_id=qa_id,
                    use_llm_evaluator=request.use_llm_evaluator,
                    use_ragas=request.use_ragas
                )
                result = await auto_evaluate(eval_request, db)
                results.append(result)
                
                if result.evaluation_success:
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"[AutoEval] 评估 QA记录 {qa_id} 失败: {e}")
                failed_count += 1
                results.append(AutoEvaluationResponse(
                    qa_record_id=qa_id,
                    evaluation_success=False,
                    llm_evaluation=None,
                    ragas_evaluation=None,
                    final_scores={},
                    error_message=str(e),
                    evaluation_time=0.0
                ))
        
        elapsed_time = time.time() - start_time
        
        logger.info(f"[AutoEval] 批量评估完成，成功: {success_count}, 失败: {failed_count}")
        
        return BatchEvaluationResponse(
            total_count=len(request.qa_record_ids),
            success_count=success_count,
            failed_count=failed_count,
            results=results,
            total_time=round(elapsed_time, 2)
        )
        
    except Exception as e:
        logger.error(f"[AutoEval] 批量评估失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

