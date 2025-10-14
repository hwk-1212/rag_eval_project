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
        self.execution_logs = []  # 存储执行日志
    
    def _log(self, step: str, message: str, details: Optional[Dict] = None):
        """
        记录执行日志
        
        Args:
            step: 步骤名称
            message: 日志消息
            details: 详细信息
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "message": message,
            "details": details or {}
        }
        self.execution_logs.append(log_entry)
    
    def _clear_logs(self):
        """清空日志"""
        self.execution_logs = []
    
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
        执行完整的RAG流程（带详细日志记录）
        
        Args:
            query: 查询文本
            **kwargs: 额外参数
            
        Returns:
            RAG执行结果
        """
        import time
        
        # 清空之前的日志
        self._clear_logs()
        
        # 记录开始
        self._log("init", f"开始执行 {self.name}", {
            "query": query[:100],
            "query_length": len(query),
            "config": self.config
        })
        
        start_time = time.time()
        
        # 检索阶段
        top_k = kwargs.get("top_k", self.config.get("top_k", 5))
        self._log("retrieve_start", f"开始检索，top_k={top_k}")
        
        retrieve_start = time.time()
        retrieved_docs = self.retrieve(query, top_k)
        retrieve_time = time.time() - retrieve_start
        
        self._log("retrieve_end", f"检索完成，找到 {len(retrieved_docs)} 个文档", {
            "doc_count": len(retrieved_docs),
            "retrieve_time": round(retrieve_time, 3),
            "scores": [round(doc.score, 4) for doc in retrieved_docs[:3]]  # 只记录前3个
        })
        
        # 生成阶段
        self._log("generate_start", "开始生成答案")
        
        generate_start = time.time()
        answer = self.generate(query, retrieved_docs)
        generate_time = time.time() - generate_start
        
        self._log("generate_end", "答案生成完成", {
            "answer_length": len(answer),
            "generate_time": round(generate_time, 3)
        })
        
        execution_time = time.time() - start_time
        
        # 记录完成
        self._log("complete", f"{self.name} 执行完成", {
            "total_time": round(execution_time, 3),
            "retrieve_time": round(retrieve_time, 3),
            "generate_time": round(generate_time, 3),
            "retrieve_ratio": round(retrieve_time / execution_time * 100, 1),
            "generate_ratio": round(generate_time / execution_time * 100, 1)
        })
        
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
                "execution_logs": self.execution_logs,  # 包含详细日志
                "timing": {
                    "total": round(execution_time, 3),
                    "retrieve": round(retrieve_time, 3),
                    "generate": round(generate_time, 3)
                }
            }
        )
        
        return result

