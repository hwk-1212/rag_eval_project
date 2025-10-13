from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RetrievedDoc:
    """检索到的文档"""
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RagResult:
    """RAG执行结果"""
    rag_technique: str
    query: str
    answer: str
    retrieved_docs: List[RetrievedDoc]
    retrieval_scores: List[float]
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class BaseRAG(ABC):
    """RAG基类 - 所有RAG技术的抽象基类"""
    
    def __init__(self, name: str, vector_store, config: Optional[Dict[str, Any]] = None):
        """
        初始化RAG
        
        Args:
            name: RAG技术名称
            vector_store: 向量存储实例
            config: 配置参数
        """
        self.name = name
        self.vector_store = vector_store
        self.config = config or {}
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            
        Returns:
            检索到的文档列表
        """
        pass
    
    @abstractmethod
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于检索结果生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 检索到的文档
            
        Returns:
            生成的答案
        """
        pass
    
    def execute(self, query: str, **kwargs) -> RagResult:
        """
        执行完整的RAG流程
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            RAG执行结果
        """
        import time
        
        start_time = time.time()
        
        # 检索
        top_k = kwargs.get("top_k", self.config.get("top_k", 5))
        retrieved_docs = self.retrieve(query, top_k)
        
        # 生成答案
        answer = self.generate(query, retrieved_docs)
        
        execution_time = time.time() - start_time
        
        # 构建结果
        result = RagResult(
            rag_technique=self.name,
            query=query,
            answer=answer,
            retrieved_docs=retrieved_docs,
            retrieval_scores=[doc.score for doc in retrieved_docs],
            execution_time=execution_time,
            metadata={
                "top_k": top_k,
                "config": self.config,
            }
        )
        
        return result

