from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from loguru import logger
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    QueryTransformationRAG,
    AdaptiveRAG,
    SelfRAG,
    CRAG,
    ContextEnrichedRAG,
    ContextualChunkHeadersRAG,
)

router = APIRouter()


# RAG技术映射
RAG_TECHNIQUES = {
    "simple_rag": SimpleRAG,
    "reranker_rag": RerankerRAG,
    "fusion_rag": FusionRAG,
    "hyde_rag": HyDERAG,
    "contextual_compression_rag": ContextualCompressionRAG,
    "query_transformation_rag": QueryTransformationRAG,
    "adaptive_rag": AdaptiveRAG,
    "self_rag": SelfRAG,
    "crag": CRAG,
    "context_enriched_rag": ContextEnrichedRAG,
    "contextual_chunk_headers_rag": ContextualChunkHeadersRAG,
}


def execute_single_rag(
    technique_name: str,
    query: str,
    document: DBDocument,
    session_id: int,
    rag_config: dict,
    llm_config: dict,
    db: Session
) -> RagResult:
    """
    执行单个RAG查询（用于并发）
    
    Args:
        technique_name: RAG技术名称
        query: 查询文本
        document: 文档对象
        session_id: 会话ID
        rag_config: RAG配置
        llm_config: LLM配置
        db: 数据库会话
        
    Returns:
        RAG执行结果
    """
    try:
        # 创建向量存储
        vector_store = VectorStore(document.vector_collection)
        
        # 创建RAG实例
        rag_class = RAG_TECHNIQUES[technique_name]
        rag = rag_class(vector_store=vector_store, config=rag_config)
        
        # 执行RAG
        rag_result = rag.execute(query, **rag_config)
        
        # 保存到数据库
        qa_record = DBQARecord(
            session_id=session_id,
            document_id=document.id,
            query=query,
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
            llm_config=llm_config,
            rag_config=rag_config,
            execution_time=rag_result.execution_time,
        )
        db.add(qa_record)
        db.commit()
        db.refresh(qa_record)
        
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
            metadata=rag_result.metadata,
            qa_record_id=qa_record.id
        )
        
        logger.info(f"RAG查询成功: {technique_name}, 查询: {query[:50]}")
        return result
        
    except Exception as e:
        logger.error(f"RAG查询失败 [{technique_name}]: {e}")
        raise


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """执行RAG问答（支持并发）"""
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
        
        document = documents[0]  # 使用第一个文档
        
        # 获取并发数（从请求中获取，默认为3）
        concurrent_num = request.rag_config.get("concurrent_num", 3)
        logger.info(f"开始并发RAG查询，并发数: {concurrent_num}, 技术数: {len(request.rag_techniques)}")
        
        results = []
        
        # 使用线程池并发执行RAG查询
        with ThreadPoolExecutor(max_workers=concurrent_num) as executor:
            # 提交所有任务
            future_to_technique = {
                executor.submit(
                    execute_single_rag,
                    technique_name,
                    request.query,
                    document,
                    session.id,
                    request.rag_config,
                    request.llm_config,
                    db
                ): technique_name
                for technique_name in request.rag_techniques
                if technique_name in RAG_TECHNIQUES
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_technique):
                technique_name = future_to_technique[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"✅ {technique_name} 查询完成")
                except Exception as e:
                    logger.error(f"❌ {technique_name} 查询失败: {e}")
                    continue
        
        if not results:
            raise HTTPException(status_code=500, detail="所有RAG技术执行失败")
        
        logger.info(f"并发查询完成，成功: {len(results)}/{len(request.rag_techniques)}")
        
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

