"""
LLM 大语言模型服务
基于 DashScope qwen-plus 模型实现流式对话生成
"""

import logging
import queue
from http import HTTPStatus
from typing import Generator, List, Dict
import dashscope
from dashscope import Generation

from config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM 大语言模型服务"""
    
    def __init__(self):
        self._setup_dashscope()
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = 20
        
    def _setup_dashscope(self):
        """配置 DashScope API"""
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        
    def _get_messages(self, user_input: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": settings.LLM_SYSTEM_PROMPT}
        ]
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": user_input})
        return messages
        
    def add_to_history(self, role: str, content: str):
        """添加消息到历史记录"""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history_length * 2:
            self.conversation_history = self.conversation_history[-self.max_history_length * 2:]
            
    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        logger.info("Conversation history cleared")
        
    def generate_stream_sync(self, user_input: str, output_queue: queue.Queue):
        """
        同步流式生成回复，将结果放入队列
        
        这个方法设计为在线程池中运行，避免阻塞事件循环
        
        Args:
            user_input: 用户输入
            output_queue: 输出队列，用于传递生成的文本片段
        """
        messages = self._get_messages(user_input)
        
        try:
            responses = Generation.call(
                model=settings.LLM_MODEL,
                messages=messages,
                result_format="message",
                stream=True,
                incremental_output=True,  # 增量输出
            )
            
            full_response = []
            
            for resp in responses:
                if resp.status_code == HTTPStatus.OK:
                    content = resp.output.choices[0].message.content
                    if content:
                        full_response.append(content)
                        # 将文本片段放入队列
                        output_queue.put({
                            'type': 'text',
                            'content': content
                        })
                        
                    if resp.output.choices[0].finish_reason == "stop":
                        usage = resp.usage
                        logger.info(
                            f"LLM usage - input: {usage.input_tokens}, "
                            f"output: {usage.output_tokens}, "
                            f"total: {usage.total_tokens}"
                        )
                else:
                    error_msg = f"LLM error: code={resp.code}, message={resp.message}"
                    logger.error(error_msg)
                    output_queue.put({
                        'type': 'error',
                        'content': resp.message
                    })
                    break
                    
            # 保存到历史记录
            full_text = "".join(full_response)
            if full_text:
                self.add_to_history("user", user_input)
                self.add_to_history("assistant", full_text)
                
            # 发送完成信号
            output_queue.put({
                'type': 'done',
                'content': full_text
            })
                
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            output_queue.put({
                'type': 'error',
                'content': str(e)
            })
            output_queue.put({
                'type': 'done',
                'content': ''
            })
