"""
实时语音交互 AI - FastAPI 后端
支持实时语音识别、对话生成、语音合成
流水线处理：ASR → LLM(流式) → TTS(流式) → 音频播放
"""

import asyncio
import base64
import json
import logging
import queue
import re
import sys
import threading
import concurrent.futures
from contextlib import asynccontextmanager
from typing import Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services import ASRService, LLMService, TTSService


def clean_text_for_tts(text: str) -> str:
    """
    清理并优化文本以供 TTS 朗读
    1. 移除 Markdown 语法符号和表情符号
    2. 优化韵律，让语音更自然
    """
    if not text:
        return ""
    
    # ===== 第一步：移除 Markdown 语法 =====
    
    # 移除代码块（整块移除）
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # 移除行内代码，保留内容
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 移除标题符号，保留文字
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    
    # 移除粗体符号，保留文字
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # 移除斜体符号，保留文字
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # 移除链接，保留文字
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # 移除图片
    text = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', text)
    
    # 移除引用符号
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    
    # 移除无序列表符号
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    
    # 移除有序列表符号
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 移除分隔线
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    
    # ===== 第二步：移除表情和特殊符号 =====
    
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\U00002702-\U000027B0"
        "\U0001F004-\U0001F0CF"
        "]+"
    )
    text = emoji_pattern.sub('', text)
    
    # 移除特殊装饰符号
    text = re.sub(r'[◆◇●○■□▲△▼▽★☆♠♣♥♦→←↑↓↔↕【】「」『』〖〗]', '', text)
    
    # ===== 第三步：韵律优化 =====
    
    # 将英文句号转为中文句号（更自然的停顿）
    text = re.sub(r'\.(\s|$)', '。', text)
    
    # 将英文逗号转为中文逗号
    text = re.sub(r',(\s|$)', '，', text)
    
    # 将英文问号转为中文问号
    text = re.sub(r'\?(\s|$)', '？', text)
    
    # 将英文感叹号转为中文感叹号
    text = re.sub(r'!(\s|$)', '！', text)
    
    # 将冒号后添加短暂停顿（用逗号代替）
    text = re.sub(r'：\s*', '，', text)
    text = re.sub(r':\s*', '，', text)
    
    # 括号内容转为逗号分隔（让TTS能读出来）
    text = re.sub(r'[（(]([^）)]+)[）)]', r'，\1，', text)
    
    # 处理破折号，转为逗号
    text = re.sub(r'——', '，', text)
    text = re.sub(r'--', '，', text)
    
    # 处理省略号，保留但限制长度
    text = re.sub(r'\.{3,}', '...', text)
    text = re.sub(r'。{2,}', '。', text)
    
    # 连续标点简化
    text = re.sub(r'[，,]{2,}', '，', text)
    text = re.sub(r'[。.]{2,}', '。', text)
    
    # ===== 第四步：清理空白 =====
    
    # 换行转为句号或逗号（让段落连贯）
    text = re.sub(r'\n+', '，', text)
    
    # 清理多余空格
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\s*([，。！？])\s*', r'\1', text)
    
    # 开头不要标点
    text = re.sub(r'^[，。！？、]+', '', text)
    
    text = text.strip()
    
    return text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 线程池执行器
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


class VoiceChatSession:
    """语音聊天会话管理"""
    
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        
        # 创建队列
        self.event_queue = queue.Queue()  # ASR/TTS 事件队列
        self.audio_queue = queue.Queue()  # TTS 音频数据队列
        self.llm_queue = queue.Queue()    # LLM 输出队列
        
        # 初始化服务
        self.asr_service = ASRService(self.event_queue)
        self.llm_service = LLMService()
        self.tts_service = TTSService(self.audio_queue, self.event_queue)
        
        self.is_active = True
        self._recognized_text = ""
        
    async def initialize(self) -> bool:
        """初始化所有服务"""
        try:
            loop = asyncio.get_event_loop()
            
            # 并行初始化 ASR 和 TTS
            asr_future = loop.run_in_executor(executor, self.asr_service.create_session)
            tts_future = loop.run_in_executor(executor, self.tts_service.create_session)
            
            asr_success, tts_success = await asyncio.gather(asr_future, tts_future)
            
            if not asr_success:
                logger.error(f"Session {self.session_id}: Failed to initialize ASR")
                return False
                
            if not tts_success:
                logger.error(f"Session {self.session_id}: Failed to initialize TTS")
                return False
                
            logger.info(f"Session {self.session_id}: All services initialized")
            return True
            
        except Exception as e:
            logger.error(f"Session {self.session_id}: Initialization error - {e}")
            return False
            
    async def send_message(self, message: dict):
        """发送消息到客户端"""
        try:
            if self.is_active:
                await self.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Session {self.session_id}: Failed to send message - {e}")
            
    async def send_audio(self, audio_data: bytes):
        """发送音频数据到客户端"""
        try:
            if self.is_active:
                audio_b64 = base64.b64encode(audio_data).decode('ascii')
                await self.websocket.send_json({
                    "type": "audio.delta",
                    "data": audio_b64
                })
        except Exception as e:
            logger.error(f"Session {self.session_id}: Failed to send audio - {e}")
            
    async def process_event_queue(self):
        """处理事件队列（ASR/TTS 事件）"""
        while self.is_active:
            try:
                try:
                    event = self.event_queue.get_nowait()
                    
                    if event['type'] == 'transcription.final':
                        self._recognized_text = event.get('text', '')
                        
                    await self.send_message(event)
                    
                except queue.Empty:
                    pass
                    
                await asyncio.sleep(0.005)
                
            except Exception as e:
                logger.error(f"Session {self.session_id}: Event queue error - {e}")
                await asyncio.sleep(0.1)
                
    async def process_audio_queue(self):
        """处理音频队列，实时发送音频到客户端"""
        while self.is_active:
            try:
                try:
                    audio_data = self.audio_queue.get_nowait()
                    await self.send_audio(audio_data)
                except queue.Empty:
                    pass
                    
                await asyncio.sleep(0.005)
                
            except Exception as e:
                logger.error(f"Session {self.session_id}: Audio queue error - {e}")
                await asyncio.sleep(0.1)
                
    async def handle_audio_input(self, audio_data: bytes):
        """处理音频输入"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, self.asr_service.send_audio, audio_data)
            
    async def process_user_input(self, text: str):
        """
        流水线处理用户输入
        
        LLM 流式生成 → 实时分句 → TTS 流式合成 → 音频实时发送
        """
        try:
            await self.send_message({"type": "response.started"})
            
            loop = asyncio.get_event_loop()
            
            # 清空 LLM 队列
            while not self.llm_queue.empty():
                try:
                    self.llm_queue.get_nowait()
                except queue.Empty:
                    break
            
            # 在线程池中启动 LLM 流式生成
            llm_future = loop.run_in_executor(
                executor,
                self.llm_service.generate_stream_sync,
                text,
                self.llm_queue
            )
            
            # 流水线处理：从 LLM 队列读取 → 分句 → TTS 合成
            buffer = ""
            full_response = []
            sentence_delimiters = ["。", "！", "？", "；", ".", "!", "?", ";", "\n"]
            llm_done = False
            
            while not llm_done:
                try:
                    # 非阻塞读取 LLM 输出
                    try:
                        item = self.llm_queue.get_nowait()
                        
                        if item['type'] == 'text':
                            content = item['content']
                            full_response.append(content)
                            buffer += content
                            
                            # 发送文本到客户端
                            await self.send_message({
                                "type": "response.delta",
                                "text": content
                            })
                            
                        elif item['type'] == 'done':
                            llm_done = True
                            
                        elif item['type'] == 'error':
                            await self.send_message({
                                "type": "error",
                                "source": "llm",
                                "message": item['content']
                            })
                            llm_done = True
                            
                    except queue.Empty:
                        await asyncio.sleep(0.01)
                        continue
                    
                    # 检查是否有完整的句子，立即发送给 TTS
                    while True:
                        earliest_pos = -1
                        for delimiter in sentence_delimiters:
                            pos = buffer.find(delimiter)
                            if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
                                earliest_pos = pos
                                
                        if earliest_pos == -1:
                            break
                            
                        sentence = buffer[:earliest_pos + 1]
                        buffer = buffer[earliest_pos + 1:]
                        
                        if sentence.strip():
                            # 清理文本后发送给 TTS
                            clean_sentence = clean_text_for_tts(sentence)
                            if clean_sentence.strip():
                                await loop.run_in_executor(
                                    executor,
                                    self.tts_service.synthesize_text_nowait,
                                    clean_sentence
                                )
                            
                except Exception as e:
                    logger.error(f"Pipeline error: {e}")
                    break
                    
            # 处理剩余的文本
            if buffer.strip():
                clean_buffer = clean_text_for_tts(buffer)
                if clean_buffer.strip():
                    await loop.run_in_executor(
                        executor,
                        self.tts_service.synthesize_text_nowait,
                        clean_buffer
                    )
                
            # 等待 LLM 线程完成
            await llm_future
            
            # 通知客户端文本生成完成
            await self.send_message({
                "type": "response.done",
                "text": "".join(full_response)
            })
            
        except Exception as e:
            logger.error(f"Session {self.session_id}: Error processing input - {e}")
            await self.send_message({
                "type": "error",
                "source": "processing",
                "message": str(e)
            })
            
    async def end_asr_and_process(self):
        """结束 ASR 会话并处理识别结果"""
        loop = asyncio.get_event_loop()
        
        await loop.run_in_executor(executor, self.asr_service.end_session)
        await asyncio.sleep(0.5)
        
        recognized_text = self._recognized_text
        self._recognized_text = ""
        
        if recognized_text:
            await self.process_user_input(recognized_text)
            
        # 重新初始化 ASR
        await loop.run_in_executor(executor, self.asr_service.create_session)
            
    def cleanup(self):
        """清理资源"""
        self.is_active = False
        try:
            self.asr_service.close()
            self.tts_service.finish()
            self.tts_service.close()
            logger.info(f"Session {self.session_id}: Cleaned up")
        except Exception as e:
            logger.error(f"Session {self.session_id}: Cleanup error - {e}")


# 存储活跃的会话
active_sessions: Dict[str, VoiceChatSession] = {}
session_counter = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Starting Voice Chat API...")
    logger.info(f"ASR Model: {settings.ASR_MODEL}")
    logger.info(f"LLM Model: {settings.LLM_MODEL}")
    logger.info(f"TTS Model: {settings.TTS_MODEL}")
    yield
    for session in active_sessions.values():
        session.cleanup()
    executor.shutdown(wait=False)
    logger.info("Voice Chat API shutdown complete")


app = FastAPI(
    title="实时语音交互 AI",
    description="支持实时语音识别、对话生成、语音合成的 AI 助手",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Voice Chat API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "active_sessions": len(active_sessions)}


@app.websocket("/ws/voice-chat")
async def voice_chat_websocket(websocket: WebSocket):
    """语音聊天 WebSocket 接口"""
    global session_counter
    
    await websocket.accept()
    
    session_counter += 1
    session_id = f"session_{session_counter}"
    
    session = VoiceChatSession(websocket, session_id)
    active_sessions[session_id] = session
    
    try:
        if not await session.initialize():
            await websocket.send_json({
                "type": "error",
                "source": "initialization",
                "message": "Failed to initialize services"
            })
            return
            
        await websocket.send_json({
            "type": "session.created",
            "session_id": session_id
        })
        
        # 启动队列处理任务
        event_task = asyncio.create_task(session.process_event_queue())
        audio_task = asyncio.create_task(session.process_audio_queue())
        
        while True:
            try:
                data = await websocket.receive_json()
                msg_type = data.get("type", "")
                
                if msg_type == "audio.input":
                    audio_b64 = data.get("data", "")
                    if audio_b64:
                        audio_data = base64.b64decode(audio_b64)
                        await session.handle_audio_input(audio_data)
                        
                elif msg_type == "audio.end":
                    await session.end_asr_and_process()
                        
                elif msg_type == "text.input":
                    text = data.get("text", "")
                    if text:
                        await session.process_user_input(text)
                        
                elif msg_type == "clear.history":
                    session.llm_service.clear_history()
                    await websocket.send_json({"type": "history.cleared"})
                    
            except WebSocketDisconnect:
                logger.info(f"Session {session_id}: Client disconnected")
                break
            except json.JSONDecodeError:
                logger.warning(f"Session {session_id}: Invalid JSON received")
                continue
            except Exception as e:
                logger.error(f"Session {session_id}: Error processing message - {e}")
                continue
                
    except Exception as e:
        logger.error(f"Session {session_id}: WebSocket error - {e}")
    finally:
        if 'event_task' in locals():
            event_task.cancel()
        if 'audio_task' in locals():
            audio_task.cancel()
        session.cleanup()
        if session_id in active_sessions:
            del active_sessions[session_id]
        logger.info(f"Session {session_id}: Closed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
