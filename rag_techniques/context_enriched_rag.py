from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import generate_rag_answer


class ContextEnrichedRAG(BaseRAG):
    """Context Enriched RAG - 上下文增强RAG
    
    流程：
    1. 向量检索获取最相关的文档chunks
    2. 对每个chunk，同时获取其前后相邻的chunks
    3. 将扩展后的上下文合并
    4. 基于增强的上下文生成答案
    
    优势：
    - 提供更完整的上下文信息
    - 避免因chunk切分导致的信息不完整
    - 保留文档的连贯性
    - 提升答案质量和准确性
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Context Enriched RAG", vector_store, config)
        self.context_size = config.get("context_size", 1) if config else 1  # 前后各扩展N个chunk
        self.system_prompt = config.get("system_prompt") if config else None
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        使用上下文增强策略检索文档
        
        Args:
            query: 查询文本
            top_k: 返回文档数量
            
        Returns:
            增强上下文的文档列表
        """
        try:
            # Step 1: 初始检索最相关的chunks
            initial_docs = self.vector_store.similarity_search(
                query=query,
                top_k=top_k
            )
            
            if not initial_docs:
                logger.warning(f"[Context Enriched RAG] 未找到文档")
                return []
            
            logger.info(f"[Context Enriched RAG] 初始检索到 {len(initial_docs)} 个文档")
            
            # Step 2: 为每个chunk扩展上下文
            enriched_docs = []
            processed_chunk_ids = set()  # 避免重复
            
            for doc in initial_docs:
                doc_id = doc.get("doc_id", "")
                chunk_index = doc.get("chunk_index", 0)
                
                # 获取该chunk的前后相邻chunks
                neighbor_chunks = self._get_neighbor_chunks(
                    doc_id=doc_id,
                    center_chunk_index=chunk_index,
                    context_size=self.context_size
                )
                
                # 合并上下文
                if neighbor_chunks:
                    # 按chunk_index排序
                    neighbor_chunks.sort(key=lambda x: x.get("chunk_index", 0))
                    
                    # 合并内容
                    enriched_content = "\n\n".join([chunk["content"] for chunk in neighbor_chunks])
                    
                    # 创建enriched文档
                    chunk_id = f"{doc_id}_enriched_{chunk_index}"
                    
                    if chunk_id not in processed_chunk_ids:
                        enriched_doc = {
                            "chunk_id": chunk_id,
                            "content": enriched_content,
                            "score": doc.get("score", 0),
                            "doc_id": doc_id,
                            "filename": doc.get("filename", ""),
                            "chunk_index": chunk_index,
                            "enriched": True,
                            "context_range": f"[{neighbor_chunks[0]['chunk_index']} - {neighbor_chunks[-1]['chunk_index']}]",
                            "num_chunks": len(neighbor_chunks)
                        }
                        enriched_docs.append(enriched_doc)
                        processed_chunk_ids.add(chunk_id)
                else:
                    # 如果无法获取相邻chunks，使用原始文档
                    if doc["chunk_id"] not in processed_chunk_ids:
                        enriched_docs.append(doc)
                        processed_chunk_ids.add(doc["chunk_id"])
            
            # 转换为RetrievedDoc对象
            retrieved_docs = []
            for doc in enriched_docs[:top_k]:  # 只返回top_k个
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],
                    score=doc["score"],
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "enriched": doc.get("enriched", False),
                        "context_range": doc.get("context_range", ""),
                        "num_chunks": doc.get("num_chunks", 1),
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            logger.info(f"[Context Enriched RAG] 返回 {len(retrieved_docs)} 个增强上下文文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Context Enriched RAG] 检索失败: {e}")
            return []
    
    def _get_neighbor_chunks(
        self,
        doc_id: str,
        center_chunk_index: int,
        context_size: int
    ) -> List[Dict]:
        """
        获取指定chunk的相邻chunks
        
        Args:
            doc_id: 文档ID
            center_chunk_index: 中心chunk的索引
            context_size: 前后扩展的chunk数量
            
        Returns:
            包含中心chunk及其相邻chunks的列表
        """
        try:
            # 计算需要查询的chunk范围
            start_index = max(0, center_chunk_index - context_size)
            end_index = center_chunk_index + context_size + 1
            
            # 查询该范围内的所有chunks
            neighbor_chunks = []
            
            for idx in range(start_index, end_index):
                chunk_id = f"{doc_id}_chunk_{idx}"
                
                # 从vector_store获取该chunk
                # 注意：这里使用一个特殊的方法来按chunk_id精确查询
                results = self.vector_store.get_by_chunk_id(chunk_id)
                
                if results:
                    neighbor_chunks.append(results[0])
            
            logger.debug(f"[Context Enriched RAG] 获取到 {len(neighbor_chunks)} 个相邻chunks (范围: {start_index}-{end_index})")
            return neighbor_chunks
            
        except Exception as e:
            logger.error(f"[Context Enriched RAG] 获取相邻chunks失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于增强上下文生成答案
        
        Args:
            query: 查询文本
            retrieved_docs: 增强上下文的文档
            
        Returns:
            生成的答案
        """
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 提取文档内容
            context = [doc.content for doc in retrieved_docs]
            
            # 调用LLM生成答案
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[Context Enriched RAG] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Context Enriched RAG] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

