from typing import List, Dict, Any, Optional
import httpx
from loguru import logger
from backend.config import settings


def call_llm(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    stream: bool = False,
    enable_thinking: bool = False,
) -> str:
    """
    调用LLM生成回答
    
    Args:
        messages: 消息列表 [{"role": "user", "content": "..."}]
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大token数
        stream: 是否流式输出
        enable_thinking: 是否启用思考模式
        
    Returns:
        LLM生成的文本
    """
    try:
        url = f"{settings.LLM_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.LLM_API_KEY}" if settings.LLM_API_KEY else "",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        
        if enable_thinking:
            payload["enable_thinking"] = True
        
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            logger.debug(f"LLM调用成功，返回长度: {len(answer)} 字符")
            return answer
            
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        raise


def generate_rag_answer(query: str, context: List[str], system_prompt: Optional[str] = None) -> str:
    """
    基于检索上下文生成答案
    
    Args:
        query: 用户问题
        context: 检索到的上下文列表
        system_prompt: 系统提示词
        
    Returns:
        生成的答案
    """
    # 构建上下文
    context_text = "\n\n".join([f"[文档{i+1}]\n{ctx}" for i, ctx in enumerate(context)])
    
    # 构建消息
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    else:
        default_system = (
            "你是一个专业的问答助手。请根据提供的文档内容回答用户的问题。"
            "如果文档中没有相关信息，请明确说明。"
        )
        messages.append({"role": "system", "content": default_system})
    
    user_content = f"""问题：{query}

参考文档：
{context_text}

请根据上述文档回答问题。"""
    
    messages.append({"role": "user", "content": user_content})
    
    return call_llm(messages)

