from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============ 文档相关 ============
class DocumentBase(BaseModel):
    filename: str
    file_type: str


class DocumentCreate(DocumentBase):
    file_path: str
    file_size: int = 0
    vector_collection: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}


class DocumentResponse(DocumentBase):
    id: int
    file_path: str
    file_size: int
    vector_collection: Optional[str]
    chunk_count: int
    upload_time: datetime
    
    class Config:
        from_attributes = True


# ============ 会话相关 ============
class SessionCreate(BaseModel):
    session_name: Optional[str] = None
    user_id: str = "default_user"


class SessionResponse(BaseModel):
    id: int
    session_name: Optional[str]
    user_id: str
    create_time: datetime
    last_active_time: datetime
    
    class Config:
        from_attributes = True


# ============ 问答相关 ============
class QueryRequest(BaseModel):
    query: str = Field(..., description="用户问题")
    document_ids: List[int] = Field(..., description="关联的文档ID列表")
    rag_techniques: List[str] = Field(
        default=["simple_rag"],
        description="要使用的RAG技术列表"
    )
    session_id: Optional[int] = None
    llm_config: Optional[Dict[str, Any]] = {}
    rag_config: Optional[Dict[str, Any]] = {}


class RetrievedDoc(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = {}


class RagResult(BaseModel):
    rag_technique: str
    answer: str
    retrieved_docs: List[RetrievedDoc]
    retrieval_scores: List[float]
    execution_time: float
    metadata: Optional[Dict[str, Any]] = {}


class QueryResponse(BaseModel):
    query: str
    results: List[RagResult]
    session_id: int
    timestamp: datetime


class QARecordResponse(BaseModel):
    id: int
    query: str
    rag_technique: str
    answer: str
    retrieved_docs: List[Dict]
    retrieval_scores: List[float]
    execution_time: float
    create_time: datetime
    
    class Config:
        from_attributes = True


# ============ 评分相关 ============
class EvaluationCreate(BaseModel):
    qa_record_id: int
    score_type: str = "human"  # human/llm/auto
    accuracy_score: Optional[float] = None
    relevance_score: Optional[float] = None
    fluency_score: Optional[float] = None
    completeness_score: Optional[float] = None
    overall_score: Optional[float] = None
    comments: Optional[str] = None
    evaluator: str = "default_user"


class EvaluationResponse(EvaluationCreate):
    id: int
    create_time: datetime
    
    class Config:
        from_attributes = True


# ============ RAG配置 ============
class RagConfig(BaseModel):
    technique: str
    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k: int = 5
    rerank: bool = False
    rerank_top_k: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = {}


class LLMConfig(BaseModel):
    model: str = "Qwen3-4B-Instruct-2507"
    temperature: float = 0.7
    max_tokens: int = 2000
    enable_thinking: bool = False
    stream: bool = False


# ============ 统计相关 ============
class ComparisonStats(BaseModel):
    """RAG技术对比统计"""
    technique: str
    total_queries: int
    avg_execution_time: float
    avg_overall_score: float
    avg_accuracy_score: float
    avg_relevance_score: float

