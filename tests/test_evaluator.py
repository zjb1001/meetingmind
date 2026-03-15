#!/usr/bin/env python3
"""
MeetingMind Evaluator 测试用例
═══════════════════════════════════════════════════════════════
"""

import unittest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.evaluator import MeetingEvaluator, EvaluationResult


class TestMeetingEvaluator(unittest.TestCase):
    """测试 MeetingEvaluator 类"""

    def setUp(self):
        """测试前准备"""
        self.evaluator = MeetingEvaluator()

        # 测试用转录文本
        self.test_transcript = """张三: 大家好，今天我们讨论一下Q2的产品规划。

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

        # 测试用会议纪要
        self.test_minutes = """# Q2产品规划会议纪要

## 基本信息
- **会议时间**: 2026-03-15 14:00
- **参会人员**: 张三、李四、王五
- **会议主题**: Q2产品规划进度同步

---

## 讨论议题

### 1. 后端技术进度
- **负责人**: 李四
- **进度**: 80%完成
- **计划**: 下周开始联调
- **状态**: ✅ 正常

### 2. 前端技术进度
- **负责人**: 王五
- **进度**: 60%完成
- **瓶颈**: 图表组件复杂，需要高保真原型支持
- **依赖**: 设计部高保真原型
- **状态**: ⚠️ 有风险

### 3. 测试准备情况
- **负责人**: 李四
- **进度**: 测试用例完成70%
- **问题**: 自动化测试框架尚未搭建
- **状态**: ⚠️ 需加急

---

## 行动项 (Action Items)

| 序号 | 负责人 | 任务描述 | 截止时间 | 优先级 | 状态 |
|:----:|:------:|----------|----------|:------:|:----:|
| 1 | 张三 | 协调设计资源并反馈 | 2026-03-16 | 🔴 高 | ⏳ 待完成 |
| 2 | 李四 | 完成自动化测试框架搭建 | 2026-03-18 | 🔴 高 | ⏳ 待完成 |
| 3 | 王五 | 跟进设计部高保真原型 | 2026-03-21 | 🟡 中 | ⏳ 待完成 |
| 4 | 张三 | 申请高配置测试服务器 | 2026-03-21 | 🟡 中 | ⏳ 待完成 |

---

## 会议总结

本次会议明确了Q2项目的技术进度和瓶颈：
1. 后端进度正常，可按计划联调
2. **前端进度滞后20%**，主要受限于设计资源，需要重点关注
3. **测试框架搭建是短期瓶颈**，需本周内解决
4. 共确定4个行动项，其中2个高优先级

**下一步**: 等待张三明天反馈设计协调结果，李四周三完成测试框架。
"""

    def test_evaluator_initialization(self):
        """测试评价器初始化"""
        self.assertIsNotNone(self.evaluator)
        self.assertEqual(self.evaluator.config.completeness_weight, 0.25)
        self.assertEqual(self.evaluator.config.accuracy_weight, 0.20)

    def test_evaluate_returns_valid_result(self):
        """测试评价返回有效结果"""
        result = self.evaluator.evaluate(self.test_transcript, self.test_minutes)

        self.assertIsInstance(result, EvaluationResult)
        self.assertGreaterEqual(result.overall_score, 0)
        self.assertLessEqual(result.overall_score, 100)
        self.assertIsInstance(result.dimensions, dict)
        self.assertIsInstance(result.strengths, list)
        self.assertIsInstance(result.weaknesses, list)
        self.assertIsInstance(result.suggestions, list)

    def test_overall_score_calculation(self):
        """测试总分计算"""
        result = self.evaluator.evaluate(self.test_transcript, self.test_minutes)

        # 验证各维度分数在合理范围内
        for dimension, score in result.dimensions.items():
            self.assertGreaterEqual(score, 0, f"{dimension} 分数不能为负")
            self.assertLessEqual(score, 100, f"{dimension} 分数不能超过100")

    def test_action_items_extraction(self):
        """测试行动项提取"""
        result = self.evaluator.evaluate(self.test_transcript, self.test_minutes)

        # 应该提取到4个行动项
        self.assertEqual(result.action_items_quality['count'], 4)

        # 所有行动项都应该有负责人、任务和截止时间
        self.assertEqual(result.action_items_quality['with_who'], 4)
        self.assertEqual(result.action_items_quality['with_what'], 4)
        self.assertEqual(result.action_items_quality['with_when'], 4)

    def test_generate_report_markdown(self):
        """测试生成Markdown报告"""
        result = self.evaluator.evaluate(self.test_transcript, self.test_minutes)
        report = self.evaluator.generate_report(result, 'markdown')

        self.assertIn('质量评价报告', report)
        self.assertIn(str(result.overall_score), report)
        self.assertIn('行动项分析', report)

    def test_generate_report_json(self):
        """测试生成JSON报告"""
        result = self.evaluator.evaluate(self.test_transcript, self.test_minutes)
        report = self.evaluator.generate_report(result, 'json')

        import json
        parsed = json.loads(report)

        self.assertEqual(parsed['overall_score'], result.overall_score)
        self.assertIn('dimensions', parsed)
        self.assertIn('strengths', parsed)

    def test_empty_input_raises_error(self):
        """测试空输入抛出错误"""
        with self.assertRaises(ValueError):
            self.evaluator.evaluate("", self.test_minutes)

        with self.assertRaises(ValueError):
            self.evaluator.evaluate(self.test_transcript, "")


class TestEvaluationEdgeCases(unittest.TestCase):
    """测试边界情况"""

    def setUp(self):
        self.evaluator = MeetingEvaluator()

    def test_no_action_items(self):
        """测试没有行动项的情况"""
        transcript = "张三: 今天天气不错。"
        minutes = "# 会议纪要\n\n没有行动项。"

        result = self.evaluator.evaluate(transcript, minutes)

        # 应该检测到缺少行动项
        self.assertEqual(result.action_items_quality['count'], 0)
        self.assertIn('无行动项', result.action_items_quality['missing_fields'])

    def test_malformed_markdown(self):
        """测试格式错误的Markdown"""
        transcript = "张三: 讨论项目。"
        minutes = "这不是标准的Markdown格式"

        result = self.evaluator.evaluate(transcript, minutes)

        # 结构分数应该较低
        self.assertLess(result.dimensions['structure'], 80)


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
