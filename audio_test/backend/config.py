import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Settings:
    """应用配置类"""
    
    # DashScope API 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    
    # ASR 配置
    ASR_MODEL: str = os.getenv("ASR_MODEL", "qwen3-asr-flash-realtime")
    ASR_SAMPLE_RATE: int = int(os.getenv("ASR_SAMPLE_RATE", "16000"))
    ASR_LANGUAGE: str = os.getenv("ASR_LANGUAGE", "zh")
    
    # LLM 配置
    LLM_MODEL: str = os.getenv("LLM_MODEL", "qwen-plus")
    LLM_SYSTEM_PROMPT: str = os.getenv(
        "LLM_SYSTEM_PROMPT", 
        """你是一个友好的AI语音助手。请遵循以下语音输出规范：

1. 使用自然口语化的表达，像朋友聊天一样
2. 句子要简短，每句话不超过20个字为佳
3. 适当使用逗号分隔长句，让语音有呼吸感
4. 避免使用复杂的书面语和专业术语
5. 不要使用表情符号、特殊符号
6. 列举内容时用"第一、第二"或"首先、其次"，而不是数字列表
7. 语气要亲切自然，可以适当使用语气词如"嗯"、"那"、"好的"
8. 回答要简洁有重点，不要太长"""
    )
    
    # TTS 配置
    TTS_MODEL: str = os.getenv("TTS_MODEL", "qwen3-tts-flash-realtime")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "Maia")
    TTS_SAMPLE_RATE: int = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
    
    # WebSocket 配置
    WS_BASE_URL: str = os.getenv("WS_BASE_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")


settings = Settings()
