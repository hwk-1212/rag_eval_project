from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from loguru import logger
from datetime import datetime

from backend.models import get_db
from backend.models.db_models import QARecord as DBQARecord, Session as DBSession, Document as DBDocument
from backend.models.schemas import QueryRequest, QueryResponse, RagResult, RetrievedDoc
from backend.core.vector_store import VectorStore
from rag_techniques import (
    SimpleRAG,
    RerankerRAG,
    FusionRAG,
    HyDERAG,
    ContextualCompressionRAG,
)

router = APIRouter()


# RAG技术映射
RAG_TECHNIQUES = {
    "simple_rag": SimpleRAG,
    "reranker_rag": RerankerRAG,
    "fusion_rag": FusionRAG,
    "hyde_rag": HyDERAG,
    "contextual_compression_rag": ContextualCompressionRAG,
}


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """执行RAG问答"""
    try:
        # 获取或创建会话
        if request.session_id:
            session = db.query(DBSession).filter(DBSession.id == request.session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
        else:
            # 创建新会话
            session = DBSession(session_name=f"会话_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            db.add(session)
            db.commit()
            db.refresh(session)
        
        # 验证文档是否存在
        documents = db.query(DBDocument).filter(DBDocument.id.in_(request.document_ids)).all()
        if not documents:
            raise HTTPException(status_code=404, detail="未找到指定的文档")
        
        results = []
        
        # 对每个RAG技术执行查询
        for technique_name in request.rag_techniques:
            if technique_name not in RAG_TECHNIQUES:
                logger.warning(f"不支持的RAG技术: {technique_name}")
                continue
            
            try:
                # 使用第一个文档的向量集合（简化处理）
                # TODO: 支持多文档检索
                document = documents[0]
                vector_store = VectorStore(document.vector_collection)
                
                # 创建RAG实例
                rag_class = RAG_TECHNIQUES[technique_name]
                rag = rag_class(vector_store=vector_store, config=request.rag_config)
                
                # 执行RAG
                rag_result = rag.execute(request.query, **request.rag_config)
                
                # 保存到数据库
                qa_record = DBQARecord(
                    session_id=session.id,
                    document_id=document.id,
                    query=request.query,
                    rag_technique=technique_name,
                    answer=rag_result.answer,
                    retrieved_docs=[
                        {
                            "chunk_id": doc.chunk_id,
                            "content": doc.content,
                            "score": doc.score,
                            "metadata": doc.metadata
                        }
                        for doc in rag_result.retrieved_docs
                    ],
                    retrieval_scores=rag_result.retrieval_scores,
                    llm_config=request.llm_config,
                    rag_config=request.rag_config,
                    execution_time=rag_result.execution_time,
                )
                db.add(qa_record)
                db.commit()
                
                # 构建响应
                result = RagResult(
                    rag_technique=technique_name,
                    answer=rag_result.answer,
                    retrieved_docs=[
                        RetrievedDoc(
                            chunk_id=doc.chunk_id,
                            content=doc.content,
                            score=doc.score,
                            metadata=doc.metadata
                        )
                        for doc in rag_result.retrieved_docs
                    ],
                    retrieval_scores=rag_result.retrieval_scores,
                    execution_time=rag_result.execution_time,
                    metadata=rag_result.metadata
                )
                results.append(result)
                
                logger.info(f"RAG查询成功: {technique_name}, 查询: {request.query[:50]}")
                
            except Exception as e:
                logger.error(f"RAG查询失败 [{technique_name}]: {e}")
                continue
        
        if not results:
            raise HTTPException(status_code=500, detail="所有RAG技术执行失败")
        
        return QueryResponse(
            query=request.query,
            results=results,
            session_id=session.id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取会话列表"""
    sessions = db.query(DBSession).offset(skip).limit(limit).all()
    return sessions


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: int,
    db: Session = Depends(get_db)
):
    """获取会话历史"""
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    qa_records = db.query(DBQARecord).filter(DBQARecord.session_id == session_id).all()
    return {
        "session": session,
        "qa_records": qa_records
    }

