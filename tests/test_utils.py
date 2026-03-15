#!/usr/bin/env python3
"""
MeetingMind Utils 测试用例
═══════════════════════════════════════════════════════════════
"""

import unittest
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import (
    retry_on_error,
    safe_cast,
    truncate,
    format_duration,
    measure_time
)


class TestRetryOnError(unittest.TestCase):
    """测试重试装饰器"""

    def test_success_on_first_try(self):
        """测试第一次尝试成功"""
        call_count = []

        @retry_on_error(max_retries=3, delay=0.01)
        def failing_function():
            call_count.append(1)
            return "success"

        result = failing_function()

        self.assertEqual(result, "success")
        self.assertEqual(len(call_count), 1)

    def test_retry_until_success(self):
        """测试重试后成功"""
        call_count = []

        @retry_on_error(max_retries=3, delay=0.01)
        def failing_function():
            call_count.append(1)
            if len(call_count) < 2:
                raise ValueError("Not yet")
            return "success"

        result = failing_function()

        self.assertEqual(result, "success")
        self.assertEqual(len(call_count), 2)

    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        @retry_on_error(max_retries=2, delay=0.01)
        def always_failing():
            raise ValueError("Always fails")

        with self.assertRaises(ValueError):
            always_failing()

    def test_specific_exception_only(self):
        """测试只重试特定异常"""
        @retry_on_error(max_retries=3, delay=0.01, exceptions=(ValueError,))
        def function():
            raise TypeError("Different error")

        with self.assertRaises(TypeError):
            function()


class TestSafeCast(unittest.TestCase):
    """测试安全类型转换"""

    def test_valid_int_conversion(self):
        """测试有效的整数转换"""
        self.assertEqual(safe_cast("123", int), 123)
        self.assertEqual(safe_cast(123.45, int), 123)

    def test_invalid_int_conversion_with_default(self):
        """测试无效整数转换使用默认值"""
        self.assertEqual(safe_cast("abc", int, 0), 0)
        self.assertEqual(safe_cast("abc", int, -1), -1)

    def test_valid_float_conversion(self):
        """测试有效的浮点数转换"""
        self.assertAlmostEqual(safe_cast("3.14", float), 3.14)

    def test_none_value(self):
        """测试None值"""
        self.assertIsNone(safe_cast(None, str))


class TestTruncate(unittest.TestCase):
    """测试文本截断"""

    def test_text_shorter_than_max(self):
        """测试文本短于最大长度"""
        text = "Short text"
        self.assertEqual(truncate(text, 100), "Short text")

    def test_text_longer_than_max(self):
        """测试文本长于最大长度"""
        text = "This is a very long text that should be truncated"
        result = truncate(text, 20)

        self.assertEqual(len(result), 20)
        self.assertTrue(result.endswith("..."))

    def test_custom_suffix(self):
        """测试自定义后缀"""
        text = "This is a very long text"
        result = truncate(text, 15, suffix=">>")

        self.assertTrue(result.endswith(">>"))

    def test_exact_length(self):
        """测试精确长度"""
        text = "Exactly 20 chars!"
        result = truncate(text, 20)

        # 不应该添加后缀
        self.assertEqual(result, text)


class TestFormatDuration(unittest.TestCase):
    """测试时长格式化"""

    def test_seconds_only(self):
        """测试只有秒"""
        self.assertEqual(format_duration(45), "45.0s")
        self.assertEqual(format_duration(0.5), "0.5s")

    def test_minutes_and_seconds(self):
        """测试分钟和秒"""
        self.assertEqual(format_duration(90), "1:30.0s")
        self.assertEqual(format_duration(125), "2:05.0s")

    def test_hours_minutes_seconds(self):
        """测试小时、分钟、秒"""
        self.assertEqual(format_duration(3665), "1:01:05.0s")
        self.assertEqual(format_duration(7200), "2:00:00.0s")


class TestMeasureTime(unittest.TestCase):
    """测试计时装饰器"""

    def test_measures_execution_time(self):
        """测试测量执行时间"""
        @measure_time
        def quick_function():
            time.sleep(0.1)
            return "done"

        result = quick_function()

        self.assertEqual(result, "done")

    def test_with_arguments(self):
        """测试带参数的函数"""
        @measure_time
        def add(a, b):
            return a + b

        result = add(2, 3)

        self.assertEqual(result, 5)


class TestUtilityFunctions(unittest.TestCase):
    """测试其他工具函数"""

    def test_edge_cases(self):
        """测试边界情况"""
        # 空字符串
        self.assertEqual(truncate("", 10), "")

        # 零时长
        self.assertEqual(format_duration(0), "0.0s")

        # 负数转换
        self.assertEqual(safe_cast("-123", int), -123)


if __name__ == '__main__':
    unittest.main(verbosity=2)
