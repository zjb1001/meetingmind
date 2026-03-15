"""
MeetingMind 配置管理模块
═══════════════════════════════════════════════════════════════
提供统一的配置管理，支持从环境变量和配置文件加载
═══════════════════════════════════════════════════════════════
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class APIConfig:
    """API配置"""
    api_key: str
    base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    model: str = "glm-4.7"
    timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    chunk: int = 1024
    format: str = "paInt16"
    input_device: Optional[int] = None


@dataclass
class EvaluationConfig:
    """评价配置"""
    completeness_weight: float = 0.25
    accuracy_weight: float = 0.20
    structure_weight: float = 0.20
    action_items_weight: float = 0.25
    readability_weight: float = 0.10


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None
    console: bool = True


@dataclass
class AppConfig:
    """应用主配置"""
    api: APIConfig = field(default_factory=APIConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # 输出配置
    output_dir: str = "."
    save_json: bool = True
    save_markdown: bool = True

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """从环境变量加载配置"""
        api_config = APIConfig(
            api_key=os.getenv('ANTHROPIC_API_KEY', '') or os.getenv('OPENAI_API_KEY', ''),
            base_url=os.getenv('ANTHROPIC_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4'),
            model=os.getenv('ANTHROPIC_MODEL', 'glm-4.7'),
            timeout=int(os.getenv('API_TIMEOUT', '60')),
            max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('API_RETRY_DELAY', '1.0'))
        )

        audio_config = AudioConfig(
            sample_rate=int(os.getenv('AUDIO_SAMPLE_RATE', '16000')),
            channels=int(os.getenv('AUDIO_CHANNELS', '1')),
            chunk=int(os.getenv('AUDIO_CHUNK', '1024')),
            input_device=int(os.getenv('AUDIO_INPUT_DEVICE', '')) if os.getenv('AUDIO_INPUT_DEVICE') else None
        )

        logging_config = LoggingConfig(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            file=os.getenv('LOG_FILE')
        )

        return cls(
            api=api_config,
            audio=audio_config,
            logging=logging_config,
            output_dir=os.getenv('OUTPUT_DIR', '.')
        )

    @classmethod
    def from_file(cls, config_file: str) -> 'AppConfig':
        """从配置文件加载 (支持JSON和TOML)"""
        path = Path(config_file)

        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        if path.suffix == '.json':
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)

        elif path.suffix in ['.toml', '.tml']:
            try:
                import tomli
                with open(path, 'rb') as f:
                    data = tomli.load(f)
                return cls.from_dict(data)
            except ImportError:
                raise ImportError("需要安装 tomli: pip install tomli")

        else:
            raise ValueError(f"不支持的配置文件格式: {path.suffix}")

    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """从字典创建配置"""
        api_data = data.get('api', {})
        audio_data = data.get('audio', {})
        logging_data = data.get('logging', {})
        eval_data = data.get('evaluation', {})

        return cls(
            api=APIConfig(**api_data) if api_data else APIConfig(),
            audio=AudioConfig(**audio_data) if audio_data else AudioConfig(),
            logging=LoggingConfig(**logging_data) if logging_data else LoggingConfig(),
            evaluation=EvaluationConfig(**eval_data) if eval_data else EvaluationConfig(),
            output_dir=data.get('output_dir', '.'),
            save_json=data.get('save_json', True),
            save_markdown=data.get('save_markdown', True)
        )

    def validate(self) -> List[str]:
        """验证配置，返回错误列表"""
        errors = []

        if not self.api.api_key:
            errors.append("未设置 API Key (ANTHROPIC_API_KEY 或 OPENAI_API_KEY)")

        if self.api.timeout <= 0:
            errors.append("API timeout 必须大于 0")

        if self.audio.sample_rate not in [8000, 16000, 44100, 48000]:
            errors.append(f"不支持的采样率: {self.audio.sample_rate}")

        if self.evaluation.completeness_weight + self.evaluation.accuracy_weight + \
           self.evaluation.structure_weight + self.evaluation.action_items_weight + \
           self.evaluation.readability_weight != 1.0:
            errors.append("评价权重总和必须为 1.0")

        return errors

    def setup_logging(self) -> None:
        """设置日志系统"""
        import logging

        level = getattr(logging, self.logging.level.upper(), logging.INFO)

        handlers = []

        if self.logging.console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            console_handler.setFormatter(logging.Formatter(self.logging.format))
            handlers.append(console_handler)

        if self.logging.file:
            Path(self.logging.file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.logging.file, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(logging.Formatter(self.logging.format))
            handlers.append(file_handler)

        # 配置根日志记录器
        logging.basicConfig(
            level=level,
            handlers=handlers,
            force=True  # Python 3.8+
        )


# 全局配置实例
_config: Optional[AppConfig] = None


def get_config(reload: bool = False) -> AppConfig:
    """获取全局配置实例"""
    global _config

    if _config is None or reload:
        _config = AppConfig.from_env()

    return _config


def set_config(config: AppConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config


if __name__ == '__main__':
    # 测试配置系统
    config = AppConfig.from_env()
    errors = config.validate()

    if errors:
        print("⚠️ 配置验证失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 配置验证通过")
        print(f"  API: {config.api.base_url}")
        print(f"  模型: {config.api.model}")
        print(f"  音频采样率: {config.audio.sample_rate}Hz")
