"""
服务模块
"""

from .asr_service import ASRService
from .tts_service import TTSService
from .llm_service import LLMService
from .interview_service import InterviewService

__all__ = ['ASRService', 'TTSService', 'LLMService', 'InterviewService']
