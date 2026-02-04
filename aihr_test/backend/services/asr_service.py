"""
ASR 语音识别服务
基于 DashScope qwen3-asr-flash-realtime 模型实现实时语音识别
"""

import base64
import logging
import queue
from typing import Optional
import dashscope
from dashscope.audio.qwen_omni import OmniRealtimeCallback, OmniRealtimeConversation, MultiModality
from dashscope.audio.qwen_omni.omni_realtime import TranscriptionParams

from config import settings

logger = logging.getLogger(__name__)


class ASRCallback(OmniRealtimeCallback):
    """ASR 回调处理类"""
    
    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.session_id: Optional[str] = None
        self._is_connected = False
        self._final_transcript = ""
        
    def on_open(self):
        """连接打开时的回调"""
        self._is_connected = True
        logger.info("ASR WebSocket connection opened")
        
    def on_close(self, code, msg):
        """连接关闭时的回调"""
        self._is_connected = False
        logger.info(f"ASR WebSocket connection closed, code: {code}, msg: {msg}")
        
    def on_event(self, response):
        """处理服务端事件 - 将事件放入队列"""
        try:
            event_type = response.get('type', '')
            
            if event_type == 'session.created':
                self.session_id = response['session']['id']
                logger.info(f"ASR session created: {self.session_id}")
                
            elif event_type == 'conversation.item.input_audio_transcription.text':
                # 实时识别的中间结果
                stash_text = response.get('stash', '')
                if stash_text:
                    self.event_queue.put({
                        'type': 'transcription.partial',
                        'text': stash_text
                    })
                    
            elif event_type == 'conversation.item.input_audio_transcription.completed':
                # 最终识别结果
                final_text = response.get('transcript', '')
                self._final_transcript = final_text
                logger.info(f"ASR transcription completed: {final_text}")
                self.event_queue.put({
                    'type': 'transcription.final',
                    'text': final_text
                })
                    
            elif event_type == 'input_audio_buffer.speech_started':
                logger.debug("Speech started detected")
                self.event_queue.put({'type': 'speech.started'})
                    
            elif event_type == 'input_audio_buffer.speech_stopped':
                logger.debug("Speech stopped detected")
                self.event_queue.put({'type': 'speech.stopped'})
                    
            elif event_type == 'error':
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                logger.error(f"ASR error: {error_msg}")
                self.event_queue.put({
                    'type': 'error',
                    'source': 'asr',
                    'message': error_msg
                })
                    
        except Exception as e:
            logger.error(f"Error handling ASR event: {e}")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def final_transcript(self) -> str:
        return self._final_transcript


class ASRService:
    """ASR 语音识别服务"""
    
    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.conversation: Optional[OmniRealtimeConversation] = None
        self.callback: Optional[ASRCallback] = None
        self._setup_dashscope()
        
    def _setup_dashscope(self):
        """配置 DashScope API"""
        dashscope.api_key = settings.DASHSCOPE_API_KEY
        
    def create_session(self) -> bool:
        """创建 ASR 会话"""
        try:
            self.callback = ASRCallback(self.event_queue)
            
            self.conversation = OmniRealtimeConversation(
                model=settings.ASR_MODEL,
                url=settings.WS_BASE_URL,
                callback=self.callback
            )
            
            # 连接到服务
            self.conversation.connect()
            
            # 配置转录参数
            transcription_params = TranscriptionParams(
                language=settings.ASR_LANGUAGE,
                sample_rate=settings.ASR_SAMPLE_RATE,
                input_audio_format="pcm"
            )
            
            # 更新会话配置
            self.conversation.update_session(
                output_modalities=[MultiModality.TEXT],
                enable_input_audio_transcription=True,
                transcription_params=transcription_params
            )
            
            logger.info("ASR session created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create ASR session: {e}")
            return False
            
    def send_audio(self, audio_data: bytes) -> bool:
        """发送音频数据进行识别"""
        try:
            if not self.conversation or not self.callback or not self.callback.is_connected:
                logger.error("ASR session not connected")
                return False
                
            audio_b64 = base64.b64encode(audio_data).decode('ascii')
            self.conversation.append_audio(audio_b64)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio data: {e}")
            return False
            
    def end_session(self):
        """结束当前会话"""
        try:
            if self.conversation:
                self.conversation.end_session()
                logger.info("ASR session ended")
        except Exception as e:
            logger.error(f"Error ending ASR session: {e}")
            
    def close(self):
        """关闭连接"""
        try:
            if self.conversation:
                self.conversation.close()
                self.conversation = None
                logger.info("ASR connection closed")
        except Exception as e:
            logger.error(f"Error closing ASR connection: {e}")
            
    @property
    def is_connected(self) -> bool:
        return self.callback.is_connected if self.callback else False
    
    @property
    def final_transcript(self) -> str:
        return self.callback.final_transcript if self.callback else ""
