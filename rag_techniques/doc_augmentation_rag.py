"""
Document Augmentation RAG - 文档增强RAG

核心思路：
1. 为每个文档块生成相关问题
2. 将这些问题也加入索引
3. 检索时同时搜索原始文档和生成的问题
4. 提高检索的召回率和多样性

优势：
- 增强语义匹配：问题可能更接近用户查询
- 提高召回率：多个角度描述同一内容
- 适合FAQ场景
"""

from typing import List, Dict, Any, Optional
import re
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import call_llm, generate_rag_answer
from backend.utils.embedding import get_single_embedding
from loguru import logger


class DocAugmentationRAG(BaseRAG):
    """
    文档增强RAG实现
    
    为每个文档块生成可回答的问题，在检索时同时利用原文和问题
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Document Augmentation RAG", vector_store, config)
        
        # 配置参数
        self.num_questions_per_chunk = config.get("num_questions_per_chunk", 3)  # 每个chunk生成几个问题
        self.enable_question_cache = config.get("enable_question_cache", True)
        self.question_weight = config.get("question_weight", 0.6)  # 问题匹配的权重
        self.content_weight = config.get("content_weight", 0.4)  # 内容匹配的权重
        
        self._question_cache = {}  # 缓存生成的问题
        
        logger.info(f"初始化 {self.name}，每块生成{self.num_questions_per_chunk}个问题")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        增强检索：同时在原文和生成的问题中检索
        """
        self._log("retrieve_start", f"开始文档增强检索，top_k={top_k}")
        
        # === Step 1: 获取所有文档块 ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",  # 使用通用查询
                top_k=100
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        self._log("chunks_loaded", f"加载了 {len(all_chunks)} 个文档块")
        
        # === Step 2: 为每个chunk生成问题（或从缓存读取） ===
        augmented_chunks = []
        for chunk in all_chunks:
            questions = self._get_or_generate_questions(chunk)
            augmented_chunks.append({
                "chunk": chunk,
                "questions": questions
            })
        
        total_questions = sum(len(ac["questions"]) for ac in augmented_chunks)
        self._log("questions_generated", f"为 {len(augmented_chunks)} 个块生成/缓存了 {total_questions} 个问题", {
            "total_questions": total_questions,
            "avg_per_chunk": round(total_questions / len(augmented_chunks), 2) if augmented_chunks else 0
        })
        
        # === Step 3: 双路检索 ===
        # 3a. 在原始内容中检索
        content_results = self._retrieve_by_content(query, all_chunks)
        
        # 3b. 在生成的问题中检索
        question_results = self._retrieve_by_questions(query, augmented_chunks)
        
        # === Step 4: 融合结果 ===
        merged_results = self._merge_results(content_results, question_results, top_k)
        
        self._log("retrieve_end", f"检索完成，返回 {len(merged_results)} 个文档", {
            "content_hits": len(content_results),
            "question_hits": len(question_results),
            "merged": len(merged_results)
        })
        
        return merged_results
    
    def _get_or_generate_questions(self, chunk: Dict) -> List[str]:
        """
        为chunk获取或生成问题
        """
        chunk_id = chunk.get("chunk_id", "")
        
        # 检查缓存
        if self.enable_question_cache and chunk_id in self._question_cache:
            return self._question_cache[chunk_id]
        
        # 生成问题（注意：vector_store返回的字段是content，不是text）
        text = chunk.get("content", "")
        questions = self._generate_questions(text)
        
        # 缓存
        if self.enable_question_cache:
            self._question_cache[chunk_id] = questions
        
        return questions
    
    def _generate_questions(self, text: str) -> List[str]:
        """
        使用LLM为文本块生成相关问题
        
        Args:
            text: 文本内容
            
        Returns:
            生成的问题列表
        """
        if not text or len(text.strip()) < 50:
            return []
        
        system_prompt = """你是一个从文本中生成相关问题的专家。
能够根据用户提供的文本生成可回答的简洁问题，重点聚焦核心信息和关键概念。"""
        
        user_prompt = f"""请根据以下文本内容生成{self.num_questions_per_chunk}个不同的、仅能通过该文本内容回答的问题：

{text[:2000]}

请严格按以下格式回复：
1. 带编号的问题列表
2. 仅包含问题
3. 不要添加任何其他内容

示例格式：
1. 问题1
2. 问题2
3. 问题3"""
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            questions_text = call_llm(
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            # 解析问题（使用正则表达式）
            pattern = r'^\d+\.\s*(.+)$'
            questions = []
            for line in questions_text.split('\n'):
                line = line.strip()
                match = re.match(pattern, line)
                if match:
                    question = match.group(1).strip()
                    if question:
                        questions.append(question)
            
            return questions[:self.num_questions_per_chunk]
            
        except Exception as e:
            logger.error(f"生成问题失败: {e}")
            return []
    
    def _retrieve_by_content(self, query: str, chunks: List[Dict]) -> List[Dict]:
        """
        在原始内容中检索
        """
        # 使用向量搜索
        results = self.vector_store.similarity_search(query=query, top_k=10)
        
        scored_results = []
        for result in results:
            scored_results.append({
                "chunk": result,
                "score": result.get("score", 0.5),
                "match_type": "content"
            })
        
        return scored_results
    
    def _retrieve_by_questions(self, query: str, augmented_chunks: List[Dict]) -> List[Dict]:
        """
        在生成的问题中检索
        """
        query_embedding = self._get_embedding(query)
        
        scored_results = []
        
        for item in augmented_chunks:
            chunk = item["chunk"]
            questions = item["questions"]
            
            if not questions:
                continue
            
            # 计算query与每个问题的相似度
            max_score = 0.0
            best_question = ""
            
            for question in questions:
                question_embedding = self._get_embedding(question)
                score = self._cosine_similarity(query_embedding, question_embedding)
                
                if score > max_score:
                    max_score = score
                    best_question = question
            
            if max_score > 0.3:  # 设置阈值
                scored_results.append({
                    "chunk": chunk,
                    "score": max_score,
                    "match_type": "question",
                    "matched_question": best_question
                })
        
        # 按分数排序
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        
        return scored_results[:10]
    
    def _merge_results(self, content_results: List[Dict], question_results: List[Dict], top_k: int) -> List[RetrievedDoc]:
        """
        融合内容检索和问题检索的结果
        """
        # 使用chunk_id去重并合并分数
        merged = {}
        
        # 处理内容检索结果
        for item in content_results:
            chunk = item["chunk"]
            chunk_id = chunk.get("chunk_id", "")
            
            if chunk_id not in merged:
                merged[chunk_id] = {
                    "chunk": chunk,
                    "content_score": item["score"] * self.content_weight,
                    "question_score": 0.0,
                    "matched_question": None
                }
            else:
                merged[chunk_id]["content_score"] = item["score"] * self.content_weight
        
        # 处理问题检索结果
        for item in question_results:
            chunk = item["chunk"]
            chunk_id = chunk.get("chunk_id", "")
            
            if chunk_id not in merged:
                merged[chunk_id] = {
                    "chunk": chunk,
                    "content_score": 0.0,
                    "question_score": item["score"] * self.question_weight,
                    "matched_question": item.get("matched_question")
                }
            else:
                merged[chunk_id]["question_score"] = item["score"] * self.question_weight
                merged[chunk_id]["matched_question"] = item.get("matched_question")
        
        # 计算总分并排序
        final_results = []
        for chunk_id, data in merged.items():
            total_score = data["content_score"] + data["question_score"]
            
            doc = RetrievedDoc(
                content=data["chunk"].get("text", ""),
                score=total_score,
                metadata={
                    "chunk_id": chunk_id,
                    "source": data["chunk"].get("source", ""),
                    "content_score": round(data["content_score"], 3),
                    "question_score": round(data["question_score"], 3),
                    "matched_question": data["matched_question"]
                }
            )
            final_results.append(doc)
        
        # 按总分排序
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results[:top_k]
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本的embedding"""
        try:
            return get_single_embedding(text)
        except Exception as e:
            logger.error(f"生成embedding失败: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0
        
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(v1, v2) / (norm1 * norm2))
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于增强检索的结果生成答案
        """
        self._log("generate_start", "开始生成答案（文档增强）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文，包含匹配的问题信息
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            matched_q = doc.metadata.get("matched_question")
            if matched_q:
                context_parts.append(
                    f"[文档{i+1}] (匹配问题: {matched_q})\n{doc.content}"
                )
            else:
                context_parts.append(
                    f"[文档{i+1}]\n{doc.content}"
                )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""你是一个专业的AI助手，基于文档增强检索的结果回答问题。
检索过程：同时在原始文档和生成的相关问题中搜索，提高召回率。

请根据提供的上下文信息回答用户问题：
1. 注意标注的"匹配问题"，它们可能与用户问题相关
2. 综合利用文档内容和问题信息
3. 保持回答的准确性和完整性"""
        
        user_prompt = f"上下文信息：\n{context}\n\n用户问题：{query}\n\n请回答："
        
        try:
            # 使用通用的RAG答案生成函数
            context = [doc.content for doc in retrieved_docs]
            answer = generate_rag_answer(
                query=query,
                context=context,
                system_prompt=system_prompt
            )
            self._log("generate_end", f"答案生成完成，长度={len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return f"生成答案时出错：{str(e)}"

