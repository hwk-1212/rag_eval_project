from typing import List
import httpx
from loguru import logger
from backend.config import settings


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    获取文本embeddings
    
    Args:
        texts: 文本列表
        
    Returns:
        embeddings列表
    """
    if not texts:
        return []
    
    try:
        url = f"{settings.EMBEDDING_BASE_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.EMBEDDING_MODEL,
            "input": texts,
            "encoding_format": "float"
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            
            logger.debug(f"成功获取 {len(texts)} 个文本的embeddings")
            return embeddings
            
    except Exception as e:
        logger.error(f"获取embeddings失败: {e}")
        raise


def get_single_embedding(text: str) -> List[float]:
    """
    获取单个文本的embedding
    
    Args:
        text: 文本
        
    Returns:
        embedding向量
    """
    return get_embeddings([text])[0]

