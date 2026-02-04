"""
AI 面试应用配置管理
"""

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
    
    # 面试配置
    MIN_FOLLOWUP_QUESTIONS: int = int(os.getenv("MIN_FOLLOWUP_QUESTIONS", "3"))  # 最少追问次数
    MAX_FOLLOWUP_QUESTIONS: int = int(os.getenv("MAX_FOLLOWUP_QUESTIONS", "5"))  # 最大追问次数
    PASS_SCORE_THRESHOLD: int = int(os.getenv("PASS_SCORE_THRESHOLD", "70"))     # 通过分数线


settings = Settings()
