"""
TTS 语音合成服务
基于 DashScope qwen3-tts-flash-realtime 模型实现实时语音合成
使用 commit 模式提高实时性和准确性
"""

import base64
import logging
import queue
import threading
from typing import Optional
import dashscope
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

from config import settings

logger = logging.getLogger(__name__)


class TTSCallback(QwenTtsRealtimeCallback):
    """TTS 回调处理类"""
    
    def __init__(self, audio_queue: queue.Queue, event_queue: queue.Queue):
        super().__init__()
        self.audio_queue = audio_queue
        self.event_queue = event_queue
        self.session_id: Optional[str] = None
        self._is_connected = False
        self.session_finished_event = threading.Event()
        
    def on_open(self) -> None:
        """连接打开时的回调"""
        self._is_connected = True
        logger.info("TTS WebSocket connection opened")
        
    def on_close(self, close_status_code, close_msg) -> None:
        """连接关闭时的回调"""
        self._is_connected = False
        logger.info(f"TTS WebSocket connection closed, code: {close_status_code}, msg: {close_msg}")
        self.session_finished_event.set()
        
    def on_event(self, response: dict) -> None:
        """处理服务端事件 - 将音频数据放入队列"""
        try:
            event_type = response.get('type', '')
            
            if event_type == 'session.created':
                self.session_id = response['session']['id']
                logger.info(f"TTS session created: {self.session_id}")
                
            elif event_type == 'response.audio.delta':
                # 接收音频数据，立即放入队列
                audio_b64 = response.get('delta', '')
                if audio_b64:
                    audio_data = base64.b64decode(audio_b64)
                    self.audio_queue.put(audio_data)
                    
            elif event_type == 'response.done':
                logger.debug("TTS response done")
                    
            elif event_type == 'session.finished':
                logger.info("TTS session finished")
                self.session_finished_event.set()
                self.event_queue.put({'type': 'audio.finished'})
                    
            elif event_type == 'error':
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                logger.error(f"TTS error: {error_msg}")
                self.event_queue.put({
                    'type': 'error',
                    'source': 'tts',
                    'message': error_msg
                })
                    
        except Exception as e:
            logger.error(f"Error handling TTS event: {e}")

    @property
    def is_connected(self) -> bool:
        return self._is_connected


class TTSService:
    """TTS 语音合成服务（使用 commit 模式）"""
    
    def __init__(self, audio_queue: queue.Queue, event_queue: queue.Queue):
        self.audio_queue = audio_queue
        self.event_queue = event_queue
        self.tts_client: Optional[QwenTtsRealtime] = None
        self.callback: Optional[TTSCallback] = None
        self._setup_dashscope()
        
    def _setup_dashscope(self):
        """配置 DashScope API"""
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        
    def create_session(self) -> bool:
        """创建 TTS 会话"""
        try:
            self.callback = TTSCallback(self.audio_queue, self.event_queue)
            
            self.tts_client = QwenTtsRealtime(
                model=settings.TTS_MODEL,
                callback=self.callback,
                url=settings.WS_BASE_URL
            )
            
            self.tts_client.connect()
            
            self.tts_client.update_session(
                voice=settings.TTS_VOICE,
                response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
                mode='commit'
            )
            
            logger.info("TTS session created successfully with commit mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create TTS session: {e}")
            return False
            
    def synthesize_text_nowait(self, text: str) -> bool:
        """
        合成文本（不等待完成，立即返回）
        
        用于流水线处理，发送后立即返回，音频数据通过队列异步接收
        """
        try:
            if not self.tts_client or not self.callback or not self.callback.is_connected:
                logger.error("TTS session not connected")
                return False
                
            if not text or not text.strip():
                return True
                
            # 发送文本并立即提交
            self.tts_client.append_text(text)
            self.tts_client.commit()
            
            logger.debug(f"TTS synthesizing: {text[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to synthesize text: {e}")
            return False
            
    def finish(self):
        """结束会话"""
        try:
            if self.tts_client and self.callback and self.callback.is_connected:
                self.tts_client.finish()
                # 等待会话结束，最多 10 秒
                self.callback.session_finished_event.wait(timeout=10.0)
                logger.info("TTS session finished")
        except Exception as e:
            logger.error(f"Error finishing TTS session: {e}")
            
    def close(self):
        """关闭连接"""
        try:
            self.tts_client = None
            logger.info("TTS connection closed")
        except Exception as e:
            logger.error(f"Error closing TTS connection: {e}")
            
    @property
    def is_connected(self) -> bool:
        return self.callback.is_connected if self.callback else False
