"""
Graph RAG - 基于知识图谱的RAG

核心思路：
1. 从文档中提取关键概念和实体
2. 构建知识图谱：节点=chunk，边=共享概念+语义相似度
3. 图遍历：基于查询相似度找起始节点，沿高权重边扩展
4. 利用图结构理解概念间关系

优势：
- 捕捉概念间的关系
- 支持多跳推理
- 适合复杂知识查询
- 发现隐含关联
"""

from typing import List, Dict, Any, Optional, Set, Tuple
import json
import re
import heapq
from collections import defaultdict
from .base import BaseRAG, RetrievedDoc, RagResult
from backend.utils.llm import call_llm, generate_rag_answer
from backend.utils.embedding import get_single_embedding
from loguru import logger


class GraphRAG(BaseRAG):
    """
    Graph RAG实现
    
    构建知识图谱并通过图遍历检索相关信息
    """
    
    def __init__(self, vector_store, config: Optional[Dict[str, Any]] = None):
        super().__init__("Graph RAG", vector_store, config)
        
        # 配置参数
        self.enable_graph_cache = config.get("enable_graph_cache", True)
        self.max_depth = config.get("max_depth", 3)  # 图遍历最大深度
        self.edge_threshold = config.get("edge_threshold", 0.6)  # 边权重阈值
        self.concept_weight = config.get("concept_weight", 0.3)  # 概念相似度权重
        self.semantic_weight = config.get("semantic_weight", 0.7)  # 语义相似度权重
        
        # 图结构缓存
        self._graph_cache = None
        self._embeddings_cache = None
        self._concepts_cache = {}
        
        logger.info(f"初始化 {self.name}，最大深度={self.max_depth}")
    
    def retrieve(self, query: str, top_k: int = 5) -> List[RetrievedDoc]:
        """
        基于知识图谱的检索
        """
        self._log("retrieve_start", f"开始Graph RAG检索，top_k={top_k}")
        
        # === Step 1: 获取所有chunk ===
        try:
            all_chunks = self.vector_store.similarity_search(
                query="文档内容",
                top_k=50  # 限制数量
            )
        except Exception as e:
            logger.warning(f"获取文档块失败: {e}")
            all_chunks = []
        
        if not all_chunks:
            self._log("retrieve_end", "未找到文档块")
            return []
        
        # 按chunk_id排序
        all_chunks.sort(key=lambda x: x.get("chunk_id", ""))
        
        self._log("chunks_loaded", f"加载了 {len(all_chunks)} 个文档块")
        
        # === Step 2: 构建或获取知识图谱 ===
        if self.enable_graph_cache and self._graph_cache is not None:
            graph = self._graph_cache
            embeddings = self._embeddings_cache
            self._log("graph_cached", "使用缓存的知识图谱")
        else:
            graph, embeddings = self._build_knowledge_graph(all_chunks[:20])  # 限制节点数量
            if self.enable_graph_cache:
                self._graph_cache = graph
                self._embeddings_cache = embeddings
            self._log("graph_built", f"构建知识图谱完成", {
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"])
            })
        
        # === Step 3: 图遍历检索 ===
        traversal_results = self._traverse_graph(query, graph, embeddings, top_k)
        
        self._log("graph_traversed", f"图遍历完成，找到 {len(traversal_results)} 个相关节点", {
            "traversed_nodes": len(traversal_results),
            "path_length": traversal_results[0].get("traversal_depth", 0) if traversal_results else 0
        })
        
        # === Step 4: 构建RetrievedDoc ===
        retrieved_docs = []
        for i, result in enumerate(traversal_results[:top_k]):
            node_id = result["node_id"]
            node_data = graph["nodes"][node_id]
            
            doc = RetrievedDoc(
                chunk_id=node_data["chunk_id"],
                content=node_data["text"],
                score=result["score"],
                metadata={
                    "source": node_data.get("source", ""),
                    "concepts": result.get("concepts", []),
                    "node_id": node_id,
                    "traversal_depth": result.get("traversal_depth", 0),
                    "connected_concepts": result.get("connected_concepts", [])
                }
            )
            retrieved_docs.append(doc)
        
        self._log("retrieve_end", f"Graph RAG检索完成，返回 {len(retrieved_docs)} 个结果")
        
        return retrieved_docs
    
    def _build_knowledge_graph(self, chunks: List[Dict]) -> Tuple[Dict, List]:
        """
        构建知识图谱
        
        Returns:
            (graph, embeddings): 图结构和节点嵌入
        """
        logger.info(f"开始构建知识图谱，共 {len(chunks)} 个节点")
        
        graph = {
            "nodes": {},  # node_id -> node_data
            "edges": []   # [(node_i, node_j, weight, shared_concepts), ...]
        }
        
        embeddings = []
        
        # === Step 1: 创建节点并提取概念 ===
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("chunk_id", f"chunk_{i}")
            text = chunk.get("content", "")
            
            # 提取概念
            concepts = self._extract_concepts(chunk_id, text)
            
            # 创建节点嵌入
            embedding = self._get_embedding(text[:500])  # 限制长度
            embeddings.append(embedding)
            
            graph["nodes"][i] = {
                "chunk_id": chunk_id,
                "text": text,
                "concepts": concepts,
                "source": chunk.get("filename", "")
            }
            
            if (i + 1) % 5 == 0:
                logger.info(f"已处理 {i+1}/{len(chunks)} 个节点")
        
        # === Step 2: 根据共享概念和语义相似度创建边 ===
        logger.info("开始创建图的边...")
        edge_count = 0
        
        for i in range(len(chunks)):
            node_i_concepts = set(graph["nodes"][i]["concepts"])
            
            for j in range(i + 1, len(chunks)):
                node_j_concepts = set(graph["nodes"][j]["concepts"])
                
                # 计算概念重叠
                shared_concepts = node_i_concepts & node_j_concepts
                
                if shared_concepts:
                    # 计算语义相似度
                    similarity = self._cosine_similarity(embeddings[i], embeddings[j])
                    
                    # 计算概念相似度
                    concept_score = len(shared_concepts) / min(len(node_i_concepts), len(node_j_concepts)) if node_i_concepts and node_j_concepts else 0
                    
                    # 综合边权重
                    edge_weight = self.semantic_weight * similarity + self.concept_weight * concept_score
                    
                    # 只添加强关联的边
                    if edge_weight > self.edge_threshold:
                        graph["edges"].append({
                            "source": i,
                            "target": j,
                            "weight": edge_weight,
                            "similarity": similarity,
                            "shared_concepts": list(shared_concepts)
                        })
                        edge_count += 1
        
        logger.info(f"知识图谱构建完成: {len(graph['nodes'])} 个节点, {edge_count} 条边")
        
        return graph, embeddings
    
    def _extract_concepts(self, chunk_id: str, text: str) -> List[str]:
        """
        从文本中提取关键概念
        """
        # 检查缓存
        if chunk_id in self._concepts_cache:
            return self._concepts_cache[chunk_id]
        
        if len(text.strip()) < 50:
            return []
        
        system_message = """从提供的文本中提取关键概念和实体。
只返回一个包含5到10个最重要的关键词、实体或概念的列表。
以JSON格式返回：{"concepts": ["概念1", "概念2", ...]}"""
        
        try:
            response = call_llm(
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"从以下文本中提取关键概念:\n\n{text[:1000]}"}
                ],
                temperature=0.0,
                max_tokens=300
            )
            
            # 解析JSON
            concepts_json = json.loads(response.strip())
            concepts = concepts_json.get("concepts", [])
            
            # 缓存
            self._concepts_cache[chunk_id] = concepts
            
            return concepts[:10]  # 最多10个概念
            
        except Exception as e:
            logger.error(f"提取概念失败: {e}")
            # 降级：简单分词
            words = text[:500].split()
            concepts = [w for w in words if len(w) > 3][:5]
            return concepts
    
    def _traverse_graph(
        self, 
        query: str, 
        graph: Dict, 
        embeddings: List, 
        top_k: int
    ) -> List[Dict]:
        """
        遍历知识图谱检索相关信息
        使用基于优先级的广度优先搜索
        """
        logger.info(f"开始图遍历，查询: {query[:50]}...")
        
        # 获取查询的嵌入
        query_embedding = self._get_embedding(query)
        
        # 计算查询与所有节点的相似度
        similarities = []
        for i, node_embedding in enumerate(embeddings):
            similarity = self._cosine_similarity(query_embedding, node_embedding)
            similarities.append((i, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 获取起始节点（最相似的top_k个）
        starting_nodes = [node for node, _ in similarities[:top_k]]
        logger.info(f"起始节点: {starting_nodes}")
        
        # 构建邻接表以便快速查找
        adjacency = defaultdict(list)
        for edge in graph["edges"]:
            adjacency[edge["source"]].append((edge["target"], edge["weight"], edge["shared_concepts"]))
            adjacency[edge["target"]].append((edge["source"], edge["weight"], edge["shared_concepts"]))
        
        # 使用优先队列进行遍历（最大堆）
        visited = set()
        results = []
        queue = []
        
        # 初始化队列
        for node in starting_nodes:
            heapq.heappush(queue, (-similarities[node][1], 0, node, []))  # (-score, depth, node, path_concepts)
        
        # 广度优先搜索
        while queue and len(results) < (top_k * 3):
            neg_score, depth, node, path_concepts = heapq.heappop(queue)
            score = -neg_score
            
            if node in visited:
                continue
            
            visited.add(node)
            
            # 添加到结果
            node_data = graph["nodes"][node]
            results.append({
                "node_id": node,
                "text": node_data["text"],
                "concepts": node_data["concepts"],
                "score": score,
                "traversal_depth": depth,
                "connected_concepts": path_concepts
            })
            
            # 探索邻居（如果未达到最大深度）
            if depth < self.max_depth:
                for neighbor, weight, shared_concepts in adjacency[node]:
                    if neighbor not in visited:
                        # 计算新分数（当前分数 * 边权重）
                        new_score = score * weight
                        new_path_concepts = path_concepts + list(shared_concepts)
                        heapq.heappush(queue, (-new_score, depth + 1, neighbor, new_path_concepts))
        
        logger.info(f"图遍历完成，访问了 {len(visited)} 个节点，返回 {len(results)} 个结果")
        
        return results
    
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
        基于图遍历结果生成答案
        """
        self._log("generate_start", "开始生成答案（Graph RAG）")
        
        if not retrieved_docs:
            return "抱歉，没有找到相关信息。"
        
        # 构建上下文，包含图结构信息
        context_parts = []
        for i, doc in enumerate(retrieved_docs):
            concepts = doc.metadata.get("concepts", [])
            depth = doc.metadata.get("traversal_depth", 0)
            connected = doc.metadata.get("connected_concepts", [])
            
            context_info = []
            if concepts:
                context_info.append(f"关键概念: {', '.join(concepts[:5])}")
            if depth > 0:
                context_info.append(f"遍历深度: {depth}")
            if connected:
                context_info.append(f"关联概念: {', '.join(set(connected[:5]))}")
            
            info_str = " | ".join(context_info) if context_info else ""
            context_parts.append(
                f"[文档{i+1}] ({info_str})\n{doc.content}"
            )
        
        context = "\n\n".join(context_parts)
        
        system_prompt = """你是一个专业的AI助手，基于知识图谱检索的结果回答问题。
检索过程：
1. 从文档构建了知识图谱（节点=文档块，边=概念关联）
2. 基于查询相似度找到起始节点
3. 沿着高权重边进行图遍历，发现相关信息

请根据提供的信息回答用户问题：
1. 注意文档中标注的"关键概念"，它们是图节点的核心
2. "遍历深度"表示通过多少跳关联找到的
3. "关联概念"显示了信息间的联系
4. 综合利用图结构理解概念间的关系"""
        
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

