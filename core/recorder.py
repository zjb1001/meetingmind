"""
音频录制模块
═══════════════════════════════════════════════════════════════
支持实时音频录制和设备管理
═══════════════════════════════════════════════════════════════
"""

import wave
import pyaudio
import threading
import signal
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from pathlib import Path

from .config import get_config
from .utils import format_duration

logger = logging.getLogger(__name__)


@dataclass
class AudioDeviceInfo:
    """音频设备信息"""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool = False


class AudioRecorder:
    """
    音频录制器

    支持功能：
    - 实时音频录制
    - 音频设备枚举
    - 录音进度监控
    """

    def __init__(
        self,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        chunk: Optional[int] = None,
        input_device: Optional[int] = None
    ):
        config = get_config()

        self.sample_rate = sample_rate or config.audio.sample_rate
        self.channels = channels or config.audio.channels
        self.chunk = chunk or config.audio.chunk
        self.input_device = input_device or config.audio.input_device

        self.format = pyaudio.paInt16
        self.recording = False
        self.frames: List[bytes] = []
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None

        logger.info(
            f"初始化录音器: {self.sample_rate}Hz, "
            f"{self.channels}ch, chunk={self.chunk}"
        )

    def list_devices(self) -> List[AudioDeviceInfo]:
        """列出可用音频输入设备"""
        p = pyaudio.PyAudio()
        devices = []

        logger.info("扫描音频设备...")

        try:
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)

                if info['maxInputChannels'] > 0:
                    device = AudioDeviceInfo(
                        index=i,
                        name=info['name'],
                        channels=int(info['maxInputChannels']),
                        sample_rate=int(info['defaultSampleRate']),
                        is_default=(i == p.get_default_input_device_info()['index'])
                    )
                    devices.append(device)

                    logger.debug(
                        f"  设备 {i}: {device.name} "
                        f"(ch: {device.channels}, rate: {device.sample_rate}Hz)"
                    )

        finally:
            p.terminate()

        return devices

    def print_devices(self) -> None:
        """打印可用设备列表"""
        devices = self.list_devices()

        if not devices:
            print("⚠️ 未检测到音频输入设备")
            return

        print("\n🎧 可用音频输入设备:")
        print("-" * 60)

        for device in devices:
            default_mark = " (默认)" if device.is_default else ""
            print(f"  [{device.index}] {device.name}{default_mark}")
            print(f"      输入通道: {device.channels} | 采样率: {device.sample_rate}Hz")

        print("-" * 60)

    def record_until_stop(self, output_file: Optional[str] = None) -> Optional[str]:
        """
        录制直到用户按下Ctrl+C

        Args:
            output_file: 输出文件路径，None 则使用临时文件

        Returns:
            录音文件路径，失败返回 None
        """
        import tempfile

        if output_file is None:
            output_file = tempfile.mktemp(suffix='.wav')

        self.frames = []
        self.recording = True
        self._start_time = None

        # 设置Ctrl+C处理
        original_handler = signal.signal(signal.SIGINT, self._signal_handler)

        try:
            p = pyaudio.PyAudio()

            # 确定输入设备
            device_index = self.input_device
            if device_index is None:
                device_info = p.get_default_input_device_info()
                device_index = device_info['index']

            logger.info(f"使用音频设备: {device_index}")

            # 打开输入流
            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )

            print(f"\n🎤 正在录制... (按 Ctrl+C 停止)")
            print(f"   设备: {p.get_device_info_by_index(device_index)['name']}")
            print(f"   格式: {self.sample_rate}Hz, {self.channels}ch")
            print()

            self._start_time = None

            # 启动进度显示线程
            progress_thread = threading.Thread(
                target=self._show_progress,
                daemon=True
            )
            progress_thread.start()

            while self.recording:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)

                    if self._start_time is None:
                        self._start_time = 0  # 标记开始

                except Exception as e:
                    logger.error(f"录音错误: {e}")
                    break

            self._stop_time = len(self.frames) * self.chunk / self.sample_rate

            # 停止和关闭流
            stream.stop_stream()
            stream.close()
            p.terminate()

            # 保存WAV文件
            if self.frames:
                with wave.open(output_file, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.format))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.frames))

                duration = len(self.frames) * self.chunk / self.sample_rate
                logger.info(f"录音保存: {output_file} ({format_duration(duration)})")
                print(f"\n💾 录音保存: {output_file}")
                print(f"   时长: {format_duration(duration)}")
                print(f"   大小: {Path(output_file).stat().st_size / 1024:.1f}KB")

                return output_file
            else:
                logger.warning("未录制到音频数据")
                return None

        except Exception as e:
            logger.error(f"录音失败: {e}")
            return None

        finally:
            signal.signal(signal.SIGINT, original_handler)
            self.recording = False

    def record_duration(self, duration: float, output_file: str) -> Optional[str]:
        """
        录制指定时长

        Args:
            duration: 录制时长（秒）
            output_file: 输出文件路径

        Returns:
            录音文件路径，失败返回 None
        """
        self.frames = []
        self.recording = True
        self._start_time = None

        try:
            p = pyaudio.PyAudio()

            device_index = self.input_device or p.get_default_input_device_info()['index']

            stream = p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk
            )

            print(f"\n🎤 录制 {format_duration(duration)}...")

            frames_needed = int(duration * self.sample_rate / self.chunk)
            frames_recorded = 0

            self._start_time = 0

            while frames_recorded < frames_needed and self.recording:
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    self.frames.append(data)
                    frames_recorded += 1

                    # 显示进度
                    progress = frames_recorded / frames_needed * 100
                    print(f"\r   进度: {progress:.1f}%", end='', flush=True)

                except Exception as e:
                    logger.error(f"录音错误: {e}")
                    break

            stream.stop_stream()
            stream.close()
            p.terminate()

            print()  # 换行

            # 保存文件
            if self.frames:
                with wave.open(output_file, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.format))
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(b''.join(self.frames))

                logger.info(f"录音保存: {output_file}")
                print(f"💾 录音保存: {output_file}")
                return output_file
            else:
                return None

        except Exception as e:
            logger.error(f"录音失败: {e}")
            return None

        finally:
            self.recording = False

    def _signal_handler(self, sig, frame):
        """处理停止信号"""
        if self.recording:
            print("\n⏹️  停止录音...")
            self.recording = False

    def _show_progress(self):
        """显示录音进度（后台线程）"""
        import time

        while self.recording:
            if self._start_time is not None:
                duration = len(self.frames) * self.chunk / self.sample_rate
                print(f"\r   时长: {format_duration(duration)}", end='', flush=True)
            time.sleep(0.5)


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试录音器
    recorder = AudioRecorder()
    recorder.print_devices()
