from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from loguru import logger

from backend.models import get_db
from backend.models.db_models import Evaluation as DBEvaluation, QARecord as DBQARecord
from backend.models.schemas import EvaluationCreate, EvaluationResponse, ComparisonStats

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

