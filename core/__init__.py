"""
MeetingMind Core Modules
═══════════════════════════════════════════════════════════════
智能会议纪要系统核心模块
═══════════════════════════════════════════════════════════════
"""

from .config import (
    AppConfig,
    APIConfig,
    AudioConfig,
    EvaluationConfig,
    LoggingConfig,
    get_config,
    set_config
)

from .recorder import AudioRecorder
from .asr import ZhipuASR
from .summarizer import MeetingSummarizer
from .evaluator import MeetingEvaluator, EvaluationResult, evaluate_meeting_minutes
from .architecture_expert import ArchitectureExpert, review_architecture
from .profiler import PerformanceProfiler, profile_performance

__all__ = [
    # Config
    'AppConfig',
    'APIConfig',
    'AudioConfig',
    'EvaluationConfig',
    'LoggingConfig',
    'get_config',
    'set_config',

    # Core Agents
    'AudioRecorder',
    'ZhipuASR',
    'MeetingSummarizer',
    'MeetingEvaluator',
    'EvaluationResult',
    'ArchitectureExpert',
    'PerformanceProfiler',

    # Convenience functions
    'evaluate_meeting_minutes',
    'review_architecture',
    'profile_performance',
]
