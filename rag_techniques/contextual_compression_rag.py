from typing import List, Dict, Any, Optional
from loguru import logger
from .base import BaseRAG, RetrievedDoc
from backend.utils.llm import call_llm, generate_rag_answer


class ContextualCompressionRAG(BaseRAG):
    """Contextual Compression RAG - 上下文压缩
    
    流程：
    1. 向量检索获取候选文档
    2. 使用LLM提取每个文档中与查询相关的关键信息
    3. 压缩文档，只保留最相关的内容
    4. 使用压缩后的上下文生成答案
    
    优势：
    - 去除无关信息，减少噪音
    - 降低LLM输入token数
    - 提高答案准确性
    - 突出关键信息
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Contextual Compression RAG", vector_store, config)
        self.compression_top_k = config.get("compression_top_k", 10) if config else 10
        self.system_prompt = config.get("system_prompt") if config else None
        self.compression_prompt_template = """请从以下文档片段中提取与问题最相关的关键信息。
只保留能够帮助回答问题的内容，去除无关信息。
如果文档与问题完全无关，请返回"无关"。

问题：{query}

文档片段：
{document}

请提取关键信息："""
    
    def _compress_document(self, query: str, document: str) -> Optional[str]:
        """
        压缩单个文档
        
        Args:
            query: 用户查询
            document: 文档内容
            
        Returns:
            压缩后的内容，如果无关则返回None
        """
        try:
            # 如果文档太短，直接返回
            if len(document) < 100:
                return document
            
            prompt = self.compression_prompt_template.format(
                query=query,
                document=document
            )
            
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            compressed = call_llm(
                messages=messages,
                temperature=0.3,  # 较低温度保持一致性
                max_tokens=500
            )
            
            # 检查是否无关
            if "无关" in compressed or len(compressed.strip()) < 20:
                logger.debug(f"[Contextual Compression] 文档被判定为无关")
                return None
            
            logger.debug(f"[Contextual Compression] 文档压缩: {len(document)} -> {len(compressed)} 字符")
            return compressed
            
        except Exception as e:
            logger.error(f"[Contextual Compression] 文档压缩失败: {e}")
            # 失败时返回原文档
            return document
    
    def _compress_documents(
        self,
        query: str,
        documents: List[Dict]
    ) -> List[Dict]:
        """
        批量压缩文档
        
        Args:
            query: 用户查询
            documents: 文档列表
            
        Returns:
            压缩后的文档列表
        """
        compressed_docs = []
        
        for i, doc in enumerate(documents):
            logger.info(f"[Contextual Compression] 压缩文档 {i+1}/{len(documents)}")
            
            compressed_content = self._compress_document(query, doc["content"])
            
            if compressed_content is not None:
                # 创建压缩后的文档
                compressed_doc = doc.copy()
                compressed_doc["original_content"] = doc["content"]
                compressed_doc["content"] = compressed_content
                compressed_doc["is_compressed"] = True
                compressed_docs.append(compressed_doc)
            else:
                logger.debug(f"[Contextual Compression] 文档 {i+1} 被过滤")
        
        logger.info(f"[Contextual Compression] 压缩完成: {len(documents)} -> {len(compressed_docs)} 个文档")
        return compressed_docs
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        带压缩的检索
        
        Args:
            query: 用户查询
            top_k: 最终返回的文档数
            
        Returns:
            压缩后的文档列表
        """
        try:
            # Step 1: 初始检索 - 获取更多候选文档
            candidates = self.vector_store.similarity_search(
                query=query,
                top_k=self.compression_top_k
            )
            
            if not candidates:
                logger.warning("[Contextual Compression] 初始检索未找到文档")
                return []
            
            logger.info(f"[Contextual Compression] 初始检索到 {len(candidates)} 个候选文档")
            
            # Step 2: 压缩文档
            compressed_docs = self._compress_documents(query, candidates)
            
            if not compressed_docs:
                logger.warning("[Contextual Compression] 所有文档被过滤")
                return []
            
            # Step 3: 选择top_k
            final_docs = compressed_docs[:top_k]
            
            # Step 4: 转换为RetrievedDoc对象
            retrieved_docs = []
            for doc in final_docs:
                retrieved_doc = RetrievedDoc(
                    chunk_id=doc["chunk_id"],
                    content=doc["content"],  # 使用压缩后的内容
                    score=doc["score"],
                    metadata={
                        "doc_id": doc.get("doc_id", ""),
                        "filename": doc.get("filename", ""),
                        "chunk_index": doc.get("chunk_index", 0),
                        "is_compressed": True,
                        "original_length": len(doc.get("original_content", "")),
                        "compressed_length": len(doc["content"]),
                        "compression_ratio": round(
                            len(doc["content"]) / len(doc.get("original_content", "x")) * 100, 2
                        ) if doc.get("original_content") else 100,
                    }
                )
                retrieved_docs.append(retrieved_doc)
            
            logger.info(f"[Contextual Compression] 检索完成，返回 {len(retrieved_docs)} 个压缩文档")
            return retrieved_docs
            
        except Exception as e:
            logger.error(f"[Contextual Compression] 检索失败: {e}")
            return []
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于压缩后的文档生成答案
        
        Args:
            query: 用户查询
            retrieved_docs: 压缩后的文档
            
        Returns:
            生成的答案
        """
        try:
            if not retrieved_docs:
                return "抱歉，没有找到相关信息来回答您的问题。"
            
            # 使用压缩后的内容
            context = [doc.content for doc in retrieved_docs]
            
            # 计算平均压缩率
            compression_ratios = [
                doc.metadata.get("compression_ratio", 100)
                for doc in retrieved_docs
            ]
            avg_compression = sum(compression_ratios) / len(compression_ratios) if compression_ratios else 100
            
            logger.info(f"[Contextual Compression] 平均压缩率: {avg_compression:.1f}%")
            
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=self.system_prompt
            )
            
            logger.info(f"[Contextual Compression] 成功生成答案，长度: {len(answer)} 字符")
            return answer
            
        except Exception as e:
            logger.error(f"[Contextual Compression] 生成答案失败: {e}")
            return f"生成答案时出现错误: {str(e)}"

