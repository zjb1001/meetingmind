"""
MeetingMind 工具模块
═══════════════════════════════════════════════════════════════
提供通用的工具函数和装饰器
═══════════════════════════════════════════════════════════════
"""

import functools
import time
import logging
from typing import Callable, Type, Tuple, Optional, Any

logger = logging.getLogger(__name__)


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
) -> Callable:
    """
    重试装饰器 - 在函数抛出异常时自动重试

    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避系数，每次重试后延迟时间乘以该系数
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数

    Returns:
        装饰后的函数

    Example:
        @retry_on_error(max_retries=3, delay=1.0)
        def api_call():
            return requests.get("https://api.example.com")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(
                            f"{func.__name__} 失败: {e} (已达到最大重试次数 {max_retries})"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_retries + 1}): {e}, "
                        f"{current_delay:.1f}秒后重试..."
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(current_delay)
                    current_delay *= backoff

            return None  # 永远不会执行到这里

        return wrapper
    return decorator


def log_execution(
    log_level: int = logging.INFO,
    log_args: bool = False,
    log_result: bool = False,
    log_exception: bool = True
) -> Callable:
    """
    日志装饰器 - 记录函数执行信息

    Args:
        log_level: 日志级别
        log_args: 是否记录函数参数
        log_result: 是否记录返回值
        log_exception: 是否记录异常

    Returns:
        装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = f"{func.__module__}.{func.__name__}"

            # 记录函数调用
            msg = f"调用 {func_name}"
            if log_args:
                msg += f" (args={args}, kwargs={kwargs})"
            logger.log(log_level, msg)

            try:
                result = func(*args, **kwargs)

                # 记录返回值
                if log_result:
                    logger.log(log_level, f"{func_name} 返回: {result}")

                return result

            except Exception as e:
                if log_exception:
                    logger.exception(f"{func_name} 抛出异常: {e}")
                raise

        return wrapper
    return decorator


def measure_time(func: Callable) -> Callable:
    """
    计时装饰器 - 测量函数执行时间

    Args:
        func: 要测量的函数

    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import time
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        logger.debug(f"{func.__name__} 执行时间: {elapsed:.2f}ms")
        return result

    return wrapper


def safe_cast(value: Any, target_type: Type, default: Any = None) -> Any:
    """
    安全类型转换

    Args:
        value: 要转换的值
        target_type: 目标类型
        default: 转换失败时的默认值

    Returns:
        转换后的值或默认值
    """
    try:
        return target_type(value)
    except (ValueError, TypeError):
        return default


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本到指定长度

    Args:
        text: 要截断的文本
        max_length: 最大长度
        suffix: 截断时的后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_duration(seconds: float) -> str:
    """
    格式化时长

    Args:
        seconds: 秒数

    Returns:
        格式化后的时长字符串 (如 "1:23:45" 或 "45.3s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:04.1f}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:04.1f}"


if __name__ == '__main__':
    # 测试工具函数
    print("测试工具模块...")

    # 测试重试装饰器
    @retry_on_error(max_retries=2, delay=0.1)
    def test_retry():
        import random
        if random.random() < 0.7:
            raise ValueError("随机失败")
        return "成功"

    print("\n测试重试装饰器:")
    for i in range(3):
        print(f"  尝试 {i+1}: ", end="")
        try:
            result = test_retry()
            print(result)
        except Exception as e:
            print(f"最终失败: {e}")

    # 测试格式化时长
    print("\n测试时长格式化:")
    print(f"  45s -> {format_duration(45)}")
    print(f"  90s -> {format_duration(90)}")
    print(f"  3665s -> {format_duration(3665)}")

    # 测试安全转换
    print("\n测试安全转换:")
    print(f"  '123' -> int: {safe_cast('123', int, 0)}")
    print(f"  'abc' -> int: {safe_cast('abc', int, 0)}")

    print("\n✅ 工具模块测试完成")
