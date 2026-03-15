#!/usr/bin/env python3
"""
MeetingMind Config 测试用例
═══════════════════════════════════════════════════════════════
"""

import unittest
import os
import tempfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import (
    AppConfig,
    APIConfig,
    AudioConfig,
    EvaluationConfig,
    LoggingConfig,
    get_config,
    set_config
)


class TestAPIConfig(unittest.TestCase):
    """测试 APIConfig"""

    def test_default_values(self):
        """测试默认值"""
        config = APIConfig(api_key="test_key")

        self.assertEqual(config.api_key, "test_key")
        self.assertEqual(config.base_url, "https://open.bigmodel.cn/api/paas/v4")
        self.assertEqual(config.model, "glm-4.7")
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.max_retries, 3)

    def test_custom_values(self):
        """测试自定义值"""
        config = APIConfig(
            api_key="custom_key",
            base_url="https://custom.api",
            model="custom-model",
            timeout=120,
            max_retries=5
        )

        self.assertEqual(config.api_key, "custom_key")
        self.assertEqual(config.base_url, "https://custom.api")
        self.assertEqual(config.model, "custom-model")
        self.assertEqual(config.timeout, 120)
        self.assertEqual(config.max_retries, 5)


class TestAudioConfig(unittest.TestCase):
    """测试 AudioConfig"""

    def test_default_values(self):
        """测试默认值"""
        config = AudioConfig()

        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.channels, 1)
        self.assertEqual(config.chunk, 1024)


class TestEvaluationConfig(unittest.TestCase):
    """测试 EvaluationConfig"""

    def test_default_weights(self):
        """测试默认权重"""
        config = EvaluationConfig()

        self.assertAlmostEqual(config.completeness_weight, 0.25)
        self.assertAlmostEqual(config.accuracy_weight, 0.20)
        self.assertAlmostEqual(config.structure_weight, 0.20)
        self.assertAlmostEqual(config.action_items_weight, 0.25)
        self.assertAlmostEqual(config.readability_weight, 0.10)

    def test_weights_sum_to_one(self):
        """测试权重总和为1"""
        config = EvaluationConfig()

        total = (
            config.completeness_weight +
            config.accuracy_weight +
            config.structure_weight +
            config.action_items_weight +
            config.readability_weight
        )

        self.assertAlmostEqual(total, 1.0)


class TestAppConfig(unittest.TestCase):
    """测试 AppConfig"""

    def test_default_initialization(self):
        """测试默认初始化"""
        config = AppConfig()

        self.assertIsInstance(config.api, APIConfig)
        self.assertIsInstance(config.audio, AudioConfig)
        self.assertIsInstance(config.evaluation, EvaluationConfig)
        self.assertIsInstance(config.logging, LoggingConfig)
        self.assertEqual(config.output_dir, ".")
        self.assertTrue(config.save_json)
        self.assertTrue(config.save_markdown)

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "api": {
                "api_key": "test_key",
                "model": "test_model"
            },
            "audio": {
                "sample_rate": 44100
            },
            "output_dir": "/tmp"
        }

        config = AppConfig.from_dict(data)

        self.assertEqual(config.api.api_key, "test_key")
        self.assertEqual(config.api.model, "test_model")
        self.assertEqual(config.audio.sample_rate, 44100)
        self.assertEqual(config.output_dir, "/tmp")

    def test_validate_missing_api_key(self):
        """测试验证缺少API Key"""
        config = AppConfig()
        config.api.api_key = ""

        errors = config.validate()

        self.assertIn("API Key", errors[0])

    def test_validate_invalid_timeout(self):
        """测试验证无效超时"""
        config = AppConfig()
        config.api.api_key = "test"
        config.api.timeout = -1

        errors = config.validate()

        self.assertTrue(any("timeout" in e.lower() for e in errors))

    def test_validate_weights_sum(self):
        """测试验证权重总和"""
        config = AppConfig()
        config.api.api_key = "test"
        config.evaluation.completeness_weight = 0.5
        config.evaluation.accuracy_weight = 0.5
        # 总和超过1

        errors = config.validate()

        self.assertTrue(any("权重" in e for e in errors))


class TestGlobalConfig(unittest.TestCase):
    """测试全局配置"""

    def setUp(self):
        """测试前清除环境变量"""
        # 保存原始环境变量
        self.original_env = os.environ.copy()

    def tearDown(self):
        """测试后恢复环境变量"""
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_get_config_from_env(self):
        """测试从环境变量获取配置"""
        os.environ['ANTHROPIC_API_KEY'] = 'env_test_key'
        os.environ['ANTHROPIC_MODEL'] = 'env_model'

        config = get_config(reload=True)

        self.assertEqual(config.api.api_key, 'env_test_key')
        self.assertEqual(config.api.model, 'env_model')

    def test_set_config(self):
        """测试设置全局配置"""
        custom_config = AppConfig()
        custom_config.api.api_key = "custom_key"

        set_config(custom_config)

        config = get_config()
        self.assertEqual(config.api.api_key, "custom_key")


class TestConfigFileLoading(unittest.TestCase):
    """测试配置文件加载"""

    def test_from_json_file(self):
        """测试从JSON文件加载"""
        config_data = {
            "api": {
                "api_key": "json_key",
                "model": "json_model"
            },
            "audio": {
                "sample_rate": 48000
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(config_data, f)
            temp_path = f.name

        try:
            config = AppConfig.from_file(temp_path)

            self.assertEqual(config.api.api_key, "json_key")
            self.assertEqual(config.api.model, "json_model")
            self.assertEqual(config.audio.sample_rate, 48000)
        finally:
            os.unlink(temp_path)

    def test_from_nonexistent_file(self):
        """测试从不存在的文件加载"""
        with self.assertRaises(FileNotFoundError):
            AppConfig.from_file("/nonexistent/config.json")


if __name__ == '__main__':
    unittest.main(verbosity=2)
