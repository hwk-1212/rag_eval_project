from typing import List, Dict, Any, Optional
from pymilvus import MilvusClient, DataType
from loguru import logger
import numpy as np
from backend.config import settings
from backend.utils.embedding import get_embeddings


class VectorStore:
    """向量存储 - 基于Milvus Lite"""
    
    def __init__(self, collection_name: str):
        """
        初始化向量存储
        
        Args:
            collection_name: 集合名称
        """
        self.collection_name = collection_name
        self.client = MilvusClient(uri=settings.MILVUS_URI)
        self.dimension = settings.EMBEDDING_DIMENSION
        
        # 创建或获取集合
        self._init_collection()
        
        logger.info(f"向量存储初始化完成: {collection_name}")
    
    def _init_collection(self):
        """初始化集合"""
        # 检查集合是否存在
        if self.client.has_collection(self.collection_name):
            logger.info(f"集合已存在: {self.collection_name}")
            return
        
        # 创建集合schema
        schema = MilvusClient.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )
        
        # 添加字段
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.dimension)
        schema.add_field(field_name="chunk_id", datatype=DataType.VARCHAR, max_length=100)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=100)
        
        # 创建索引参数
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type="FLAT",  # Milvus Lite支持的索引类型
            metric_type="COSINE",  # 余弦相似度
        )
        
        # 创建集合
        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )
        
        logger.info(f"创建集合成功: {self.collection_name}")
    
    def add_documents(self, chunks: List[Any]) -> int:
        """
        添加文档块到向量库
        
        Args:
            chunks: Chunk对象列表
            
        Returns:
            添加的文档数量
        """
        if not chunks:
            return 0
        
        try:
            # 提取文本内容
            texts = [chunk.content for chunk in chunks]
            
            # 获取embeddings
            embeddings = get_embeddings(texts)
            
            # 准备插入数据
            data = []
            for chunk, embedding in zip(chunks, embeddings):
                item = {
                    "vector": embedding,
                    "chunk_id": chunk.doc_id,
                    "content": chunk.content[:65535],  # 限制长度
                    "doc_id": chunk.metadata.get("doc_id", ""),
                    "filename": chunk.metadata.get("filename", ""),
                    "chunk_index": chunk.chunk_index,
                }
                data.append(item)
            
            # 插入数据
            result = self.client.insert(
                collection_name=self.collection_name,
                data=data
            )
            
            logger.info(f"成功添加 {len(data)} 个文档块到向量库")
            return len(data)
            
        except Exception as e:
            logger.error(f"添加文档到向量库失败: {e}")
            raise
    
    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            filter_expr: 过滤表达式
            
        Returns:
            搜索结果列表
        """
        try:
            # 获取查询向量
            query_embedding = get_embeddings([query])[0]
            
            # 执行搜索
            search_params = {
                "metric_type": "COSINE",
                "params": {},
            }
            
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_embedding],
                limit=top_k,
                search_params=search_params,
                output_fields=["chunk_id", "content", "doc_id", "filename", "chunk_index"],
                filter=filter_expr,
            )
            
            # 格式化结果
            formatted_results = []
            for hit in results[0]:
                formatted_results.append({
                    "chunk_id": hit.get("chunk_id", ""),
                    "content": hit.get("content", ""),
                    "score": float(hit.get("distance", 0.0)),
                    "doc_id": hit.get("doc_id", ""),
                    "filename": hit.get("filename", ""),
                    "chunk_index": hit.get("chunk_index", 0),
                })
            
            logger.info(f"检索完成，返回 {len(formatted_results)} 个结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            raise
    
    def delete_by_doc_id(self, doc_id: str) -> bool:
        """
        根据文档ID删除所有相关的块
        
        Args:
            doc_id: 文档ID
            
        Returns:
            是否删除成功
        """
        try:
            filter_expr = f'doc_id == "{doc_id}"'
            self.client.delete(
                collection_name=self.collection_name,
                filter=filter_expr
            )
            logger.info(f"删除文档成功: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        try:
            stats = self.client.get_collection_stats(self.collection_name)
            return stats
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}
    
    def drop_collection(self):
        """删除集合"""
        try:
            self.client.drop_collection(self.collection_name)
            logger.info(f"删除集合成功: {self.collection_name}")
        except Exception as e:
            logger.error(f"删除集合失败: {e}")

