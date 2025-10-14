"""
Proposition Chunking RAG - 命题分块RAG

核心思路：
1. 将文档分解为原子化、自包含的命题
2. 每个命题表达单一事实，独立可理解
3. 避免代词和模糊指代，使用完整实体名
4. 命题级别的检索更精确

优势：
- 细粒度的语义单元
- 避免上下文依赖
- 提高检索精度
- 适合事实型问答
"""

from typing import List, Dict, Any, Optional
import re
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import call_llm, generate_rag_answer
from loguru import logger


class PropositionChunkingRAG(BaseRAG):
    """
    命题分块RAG实现
    
    将文档分解为原子化命题，在命题级别进行检索
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Proposition Chunking RAG", vector_store, config)
        
        # 配置参数
        self.enable_proposition_cache = config.get("enable_proposition_cache", True)
        self.min_proposition_quality = config.get("min_proposition_quality", 7)  # 质量阈值
        
        self._proposition_cache = {}  # 缓存生成的命题
        
        logger.info(f"初始化 {self.name}，质量阈值={self.min_proposition_quality}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        命题级别检索
        """
        self._log("retrieve_start", f"开始命题分块检索，top_k={top_k}")
        
        # === Step 1: 获取所有chunk ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",
                top_k=50  # 限制数量避免过多
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        
        if not all_chunks:
            self._log("retrieve_end", "未找到文档块")
            return []
        
        self._log("chunks_loaded", f"加载了 {len(all_chunks)} 个文档块")
        
        # === Step 2: 为每个chunk生成命题 ===
        all_propositions = []
        
        for chunk in all_chunks[:10]:  # 限制处理数量，避免太慢
            chunk_id = chunk.get("chunk_id", "")
            content = chunk.get("content", "")
            
            if len(content.strip()) < 50:
                continue
            
            # 生成或获取缓存的命题
            propositions = self._get_or_generate_propositions(chunk_id, content)
            
            for prop_text in propositions:
                all_propositions.append({
                    "text": prop_text,
                    "source_chunk_id": chunk_id,
                    "source_content": content,
                    "source": chunk.get("filename", "")
                })
        
        self._log("propositions_generated", f"生成了 {len(all_propositions)} 个命题", {
            "total_propositions": len(all_propositions),
            "from_chunks": len(all_chunks[:10])
        })
        
        if not all_propositions:
            # 降级到普通chunk检索
            return self._fallback_retrieve(query, all_chunks, top_k)
        
        # === Step 3: 在命题中检索最相关的 ===
        # 简化版：基于文本相似度排序
        query_lower = query.lower()
        
        # 计算每个命题与query的简单相似度（关键词匹配）
        for prop in all_propositions:
            prop_lower = prop["text"].lower()
            
            # 简单的关键词匹配得分
            query_words = set(query_lower.split())
            prop_words = set(prop_lower.split())
            common_words = query_words & prop_words
            
            if len(query_words) > 0:
                prop["match_score"] = len(common_words) / len(query_words)
            else:
                prop["match_score"] = 0.0
        
        # 按匹配得分排序
        all_propositions.sort(key=lambda x: x["match_score"], reverse=True)
        
        # === Step 4: 构建RetrievedDoc（合并同一chunk的命题） ===
        chunk_propositions = {}
        for prop in all_propositions[:top_k * 3]:  # 取前几个命题
            chunk_id = prop["source_chunk_id"]
            if chunk_id not in chunk_propositions:
                chunk_propositions[chunk_id] = {
                    "propositions": [],
                    "source": prop["source"],
                    "source_content": prop["source_content"]
                }
            chunk_propositions[chunk_id]["propositions"].append({
                "text": prop["text"],
                "score": prop["match_score"]
            })
        
        retrieved_docs = []
        for chunk_id, data in list(chunk_propositions.items())[:top_k]:
            # 合并命题
            prop_texts = [p["text"] for p in data["propositions"]]
            merged_content = "\n\n".join(prop_texts)
            
            avg_score = sum(p["score"] for p in data["propositions"]) / len(data["propositions"])
            
            doc = RetrievedDoc(
                chunk_id=chunk_id,
                content=merged_content,
                score=avg_score,
                metadata={
                    "source": data["source"],
                    "num_propositions": len(data["propositions"]),
                    "proposition_scores": [round(p["score"], 3) for p in data["propositions"]],
                    "original_content": data["source_content"][:200] + "..."
                }
            )
            retrieved_docs.append(doc)
        
        self._log("retrieve_end", f"命题检索完成，返回 {len(retrieved_docs)} 个结果")
        
        return retrieved_docs
    
    def _get_or_generate_propositions(self, chunk_id: str, content: str) -> List[str]:
        """
        获取或生成命题
        """
        # 检查缓存
        if self.enable_proposition_cache and chunk_id in self._proposition_cache:
            return self._proposition_cache[chunk_id]
        
        # 生成命题
        propositions = self._generate_propositions(content)
        
        # 缓存
        if self.enable_proposition_cache:
            self._proposition_cache[chunk_id] = propositions
        
        return propositions
    
    def _generate_propositions(self, content: str) -> List[str]:
        """
        使用LLM生成命题
        """
        system_prompt = """请将以下文本分解为简单的自包含命题。确保每个命题符合以下标准：

1. 表达单一事实：每个命题应陈述一个具体事实或主张
2. 独立可理解：命题应自成体系，无需额外上下文即可理解
3. 使用全称而非代词：避免使用代词或模糊指代，使用完整的实体名称
4. 包含相关日期/限定条件：如适用应包含必要日期、时间和限定条件以保持准确性
5. 保持单一主谓关系：聚焦单个主体及其对应动作或属性

请仅输出命题列表（每行一个），不要包含编号或其他额外文本。"""
        
        user_prompt = f"要转换为命题的文本:\n\n{content[:1500]}"  # 限制长度
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = call_llm(
                messages=messages,
                temperature=0,
                max_tokens=800
            )
            
            # 解析命题
            raw_propositions = response.strip().split('\n')
            
            # 清理命题（移除编号、项目符号等）
            clean_propositions = []
            for prop in raw_propositions:
                # 移除编号和项目符号
                cleaned = re.sub(r'^\s*(\d+\.|\-|\*)\s*', '', prop).strip()
                if cleaned and len(cleaned) > 10:  # 过滤过短的命题
                    clean_propositions.append(cleaned)
            
            return clean_propositions[:10]  # 最多返回10个命题
            
        except Exception as e:
            logger.error(f"生成命题失败: {e}")
            # 降级：简单按句号分割
            sentences = content.split('。')
            return [s.strip() + '。' for s in sentences if len(s.strip()) > 10][:5]
    
    def _fallback_retrieve(self, query: str, all_chunks: List[Dict], top_k: int) -> List[RetrievedDoc]:
        """
        降级方案：使用普通chunk检索
        """
        logger.warning("命题生成失败，降级到普通chunk检索")
        
        query_results = self.vector_store.similarity_search(query=query, top_k=top_k)
        
        retrieved_docs = []
        for result in query_results:
            doc = RetrievedDoc(
                chunk_id=result.get("chunk_id", ""),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                metadata={
                    "source": result.get("filename", ""),
                    "fallback": True
                }
            )
            retrieved_docs.append(doc)
        
        return retrieved_docs
    
    def generate(self, query: str, retrieved_docs: List[RetrievedDoc]) -> str:
        """
        基于命题生成答案
        """
        self._log("generate_start", "开始生成答案（命题分块）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            num_props = doc.metadata.get("num_propositions", 0)
            context_parts.append(
                f"[文档{i+1}] (包含 {num_props} 个命题)\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = """你是一个专业的AI助手，基于命题分块检索的结果回答问题。
检索过程：文档被分解为原子化的命题，每个命题表达单一事实且独立可理解。

请根据提供的命题信息回答用户问题：
1. 每个命题都是独立的事实陈述
2. 综合多个命题形成完整回答
3. 保持回答的准确性和逻辑性"""
        
        try:
            context_list = [doc.content for doc in retrieved_docs]
            answer = generate_rag_answer(
                query=query,
                context=context_list,
                system_prompt=system_prompt
            )
            self._log("generate_end", f"答案生成完成，长度={len(answer)}")
            return answer
            
        except Exception as e:
            logger.error(f"生成答案失败: {e}")
            return f"生成答案时出错：{str(e)}"

