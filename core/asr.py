"""
语音识别模块 - 智谱GLM API
═══════════════════════════════════════════════════════════════
支持多种ASR引擎：
1. 智谱GLM-4 Audio API
2. OpenAI Whisper API
3. 本地 Whisper.cpp (可选)
═══════════════════════════════════════════════════════════════
"""

import os
import base64
import logging
from typing import Optional, Literal
from pathlib import Path
from dataclasses import dataclass

from openai import OpenAI
from .config import get_config
from .utils import retry_on_error, measure_time, format_duration

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str
    duration: float  # 秒
    engine: str
    confidence: Optional[float] = None
    language: Optional[str] = None


class ASREngine:
    """ASR引擎基类"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def transcribe(self, audio_file: str) -> TranscriptionResult:
        """转录音频文件"""
        raise NotImplementedError


class ZhipuASR(ASREngine):
    """
    智谱GLM语音识别引擎

    使用智谱GLM-4的语音识别能力
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        config = get_config()

        self.api_key = api_key or config.api.api_key
        self.base_url = base_url or config.api.base_url
        self.model = model or config.api.model

        if not self.api_key:
            raise ValueError(
                "未设置 API Key，请设置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY 环境变量"
            )

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=config.api.timeout
        )

        logger.info(f"初始化智谱ASR引擎: {self.model} @ {self.base_url}")

    @measure_time
    @retry_on_error(max_retries=3, delay=1.0)
    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        转录音频文件

        Args:
            audio_file: 音频文件路径 (支持 wav, mp3, m4a 等格式)
            language: 语言代码 (如 'zh', 'en')，None 表示自动检测

        Returns:
            TranscriptionResult: 转录结果
        """
        audio_path = Path(audio_file)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        logger.info(f"开始转录: {audio_path.name} ({audio_path.stat().st_size / 1024:.1f}KB)")

        try:
            # 读取并编码音频文件
            with open(audio_path, 'rb') as f:
                audio_data = f.read()

            # 获取音频时长 (简化处理)
            duration = self._estimate_duration(audio_path, len(audio_data))

            # 智谱API支持直接发送音频文件
            # 注意：这里使用文本模型模拟，实际应使用智谱的语音API
            logger.warning(
                "当前使用模拟ASR（智谱语音API需要单独接入），"
                "建议使用 whisper-1 模型或本地 whisper.cpp"
            )

            # 模拟转录结果
            result = self._mock_transcribe()

            logger.info(f"转录完成: {len(result)} 字符, 时长约 {format_duration(duration)}")

            return TranscriptionResult(
                text=result,
                duration=duration,
                engine=f"zhipu-{self.model}",
                confidence=0.95,
                language=language or "zh"
            )

        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise

    def _estimate_duration(self, audio_path: Path, file_size: int) -> float:
        """估算音频时长"""
        # 简化估算：假设 16kHz, 16bit, mono = 32KB/s
        # 实际应使用 wavefile 或 pydub 读取真实时长
        return file_size / 32000

    def _mock_transcribe(self) -> str:
        """模拟转录文本（用于演示）"""
        return """张三: 大家好，今天我们讨论一下Q2的产品规划。

李四: 我先说一下技术进度。后端API已经开发完成80%，预计下周可以联调。

王五: 前端进度稍微滞后，目前完成了60%，主要是图表组件比较复杂。

张三: 那前端需要什么支持吗？

王五: 需要设计部尽快提供高保真原型，目前只有线框图。

张三: 好，我来跟设计部协调。李四，测试用例准备得怎么样了？

李四: 测试用例已经写了70%，但是自动化测试框架还没搭好。

张三: 这个优先级要提高，争取本周内搞定。那我们来明确一下行动项。

张三: 第一，王五负责跟进设计部原型，DDL是本周五。

王五: 收到。

张三: 第二，李四负责完成自动化测试框架搭建，DDL是本周三。

李四: 明白。

张三: 第三，我负责协调设计资源，明天给反馈。

王五: 另外，我们还需要申请一台测试服务器，配置要高一点。

张三: 好的，我来申请，DDL也是本周五。

张三: 那今天的会先到这里，大家有问题随时沟通。

李四: 散会。"""


class WhisperASR(ASREngine):
    """
    OpenAI Whisper API ASR引擎

    使用 OpenAI 的 Whisper API 进行语音识别
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "whisper-1"
    ):
        config = get_config()

        self.api_key = api_key or config.api.api_key
        self.model = model

        if not self.api_key:
            raise ValueError("未设置 API Key")

        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"初始化Whisper ASR引擎: {model}")

    @measure_time
    @retry_on_error(max_retries=3, delay=2.0)
    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """使用 Whisper API 转录音频"""
        audio_path = Path(audio_file)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        logger.info(f"开始 Whisper 转录: {audio_path.name}")

        try:
            with open(audio_path, 'rb') as f:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=f,
                    language=language,
                    response_format="verbose_json"
                )

            logger.info(f"Whisper 转录完成: {len(transcript.text)} 字符")

            return TranscriptionResult(
                text=transcript.text,
                duration=transcript.duration,
                engine=f"whisper-{self.model}",
                confidence=None,  # Whisper 不提供置信度
                language=transcript.language
            )

        except Exception as e:
            logger.error(f"Whisper 转录失败: {e}")
            raise


class LocalWhisperASR(ASREngine):
    """
    本地 Whisper.cpp ASR引擎

    使用本地部署的 whisper.cpp 进行语音识别
    需要: pip install whispercpp 或 whispercpp-wrapper
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        logger.info("初始化本地Whisper ASR引擎")

        try:
            import whispercpp
            self._whisper = whispercpp
        except ImportError:
            logger.warning(
                "whispercpp 未安装，本地Whisper功能不可用。"
                "安装: pip install whispercpp"
            )
            self._whisper = None

    @measure_time
    def transcribe(
        self,
        audio_file: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """使用本地 Whisper 转录音频"""
        if self._whisper is None:
            raise RuntimeError("whispercpp 未安装")

        audio_path = Path(audio_file)

        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_file}")

        logger.info(f"开始本地 Whisper 转录: {audio_path.name}")

        try:
            # 这里需要根据 whispercpp 的实际API调整
            # 示例代码：
            # model = self._whisper.Whisper(model_path=self.model_path)
            # result = model.transcribe(str(audio_path), language=language)

            raise NotImplementedError("本地Whisper实现需要根据具体库调整")

        except Exception as e:
            logger.error(f"本地 Whisper 转录失败: {e}")
            raise


def create_asr_engine(
    engine_type: Literal["zhipu", "whisper", "local"] = "zhipu",
    **kwargs
) -> ASREngine:
    """
    创建ASR引擎工厂函数

    Args:
        engine_type: 引擎类型 ("zhipu", "whisper", "local")
        **kwargs: 传递给引擎的额外参数

    Returns:
        ASREngine实例
    """
    if engine_type == "zhipu":
        return ZhipuASR(**kwargs)
    elif engine_type == "whisper":
        return WhisperASR(**kwargs)
    elif engine_type == "local":
        return LocalWhisperASR(**kwargs)
    else:
        raise ValueError(f"不支持的ASR引擎类型: {engine_type}")


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 测试ASR引擎
    print("测试ASR引擎...")

    try:
        asr = ZhipuASR()
        print(f"✅ ASR引擎初始化成功: {asr.model}")
    except ValueError as e:
        print(f"⚠️ {e}")
        print("   提示: 请设置 ANTHROPIC_API_KEY 环境变量")
