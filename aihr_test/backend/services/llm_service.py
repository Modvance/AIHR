"""
LLM 服务
基于 DashScope 的大语言模型服务，支持流式输出
主要用于非面试场景的通用对话（面试逻辑在 interview_service.py 中处理）
"""

import logging
import queue
from http import HTTPStatus
from typing import List, Dict, Optional

from dashscope import Generation
import dashscope

from config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 对话服务"""
    
    def __init__(self, system_prompt: str = ""):
        self._setup_dashscope()
        self.system_prompt = system_prompt or "你是一个友好的AI助手。"
        self.conversation_history: List[Dict] = []
        self.max_history_length = 20
        
    def _setup_dashscope(self):
        """配置 DashScope API"""
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        
    def set_system_prompt(self, prompt: str):
        """设置系统提示词"""
        self.system_prompt = prompt
        
    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
            
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
        
    def generate_stream_sync(self, user_input: str, output_queue: queue.Queue):
        """
        流式生成回复（同步方法，用于在线程池中执行）
        
        Args:
            user_input: 用户输入
            output_queue: 输出队列，用于传递生成的文本片段
        """
        try:
            # 添加用户消息
            self.add_message("user", user_input)
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history
            
            # 发起流式请求
            responses = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
                temperature=0.7,
                stream=True,
                incremental_output=True,
            )
            
            content_parts = []
            for resp in responses:
                if resp.status_code == HTTPStatus.OK:
                    content = resp.output.choices[0].message.content
                    content_parts.append(content)
                    output_queue.put({'type': 'text', 'content': content})
                    
                    if resp.output.choices[0].finish_reason == "stop":
                        break
                else:
                    output_queue.put({
                        'type': 'error',
                        'content': f"请求失败: code={resp.code}, message={resp.message}"
                    })
                    return
            
            # 保存助手回复
            full_response = "".join(content_parts)
            self.add_message("assistant", full_response)
            
            output_queue.put({'type': 'done'})
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            output_queue.put({'type': 'error', 'content': str(e)})
