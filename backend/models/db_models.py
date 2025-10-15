from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class Document(Base):
    """文档表"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    vector_collection = Column(String(100))  # Milvus collection名称
    chunk_count = Column(Integer, default=0)
    upload_time = Column(DateTime, default=datetime.now)
    meta_data = Column("metadata", JSON, default={})
    
    # 关联关系
    qa_records = relationship("QARecord", back_populates="document")


class Session(Base):
    """会话表"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_name = Column(String(255))
    user_id = Column(String(100), default="default_user")
    create_time = Column(DateTime, default=datetime.now)
    last_active_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    meta_data = Column("metadata", JSON, default={})
    
    # 关联关系
    qa_records = relationship("QARecord", back_populates="session")


class QARecord(Base):
    """问答记录表"""
    __tablename__ = "qa_records"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    document_id = Column(Integer, ForeignKey("documents.id"))
    query = Column(Text, nullable=False)
    rag_technique = Column(String(100), nullable=False)  # RAG技术名称
    answer = Column(Text)
    retrieved_docs = Column(JSON, default=[])  # 检索到的文档片段
    retrieval_scores = Column(JSON, default=[])  # 检索分数
    llm_config = Column(JSON, default={})  # LLM配置
    rag_config = Column(JSON, default={})  # RAG配置
    execution_time = Column(Float, default=0.0)  # 执行时间(秒)
    create_time = Column(DateTime, default=datetime.now)
    
    # 关联关系
    session = relationship("Session", back_populates="qa_records")
    document = relationship("Document", back_populates="qa_records")
    evaluations = relationship("Evaluation", back_populates="qa_record")


class Evaluation(Base):
    """评分表"""
    __tablename__ = "evaluations"
    
    id = Column(Integer, primary_key=True, index=True)
    qa_record_id = Column(Integer, ForeignKey("qa_records.id"))
    score_type = Column(String(50), nullable=False)  # human/llm/auto
    
    # 评分维度（LLM评估）
    accuracy_score = Column(Float)  # 准确性
    relevance_score = Column(Float)  # 相关性
    faithfulness_score = Column(Float)  # 忠实度
    coherence_score = Column(Float)  # 连贯性
    fluency_score = Column(Float)  # 流畅性
    conciseness_score = Column(Float)  # 简洁性
    completeness_score = Column(Float)  # 完整性
    overall_score = Column(Float)  # 总体评分
    
    comments = Column(Text)  # 评价说明
    evaluator = Column(String(100))  # 评测者
    create_time = Column(DateTime, default=datetime.now)
    meta_data = Column("metadata", JSON, default={})
    
    # 关联关系
    qa_record = relationship("QARecord", back_populates="evaluations")

