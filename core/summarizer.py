"""
会议纪要生成器 - 使用LLM提取结构化信息
═══════════════════════════════════════════════════════════════
核心功能：
1. 从会议转录文本生成结构化纪要
2. 提取参会人员、议题、行动项
3. 自动识别会议主题和结论
═══════════════════════════════════════════════════════════════
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from openai import OpenAI
from .config import get_config
from .utils import retry_on_error, measure_time, truncate

logger = logging.getLogger(__name__)


class MeetingSummarizer:
    """
    会议纪要生成器

    使用大语言模型从会议转录文本生成结构化纪要
    """

    # 默认系统提示词
    DEFAULT_SYSTEM_PROMPT = """你是一个专业的会议纪要助手，擅长从会议记录中提取关键信息和行动项。

你的任务是：
1. 提取参会人员列表
2. 总结主要讨论议题（每个议题用一句话概括）
3. 重点提取行动项：谁(Who) + 做什么(What) + 截止时间(When)
4. 识别会议中的关键决策和结论
5. 使用Markdown格式输出"""

    # 默认输出格式
    DEFAULT_OUTPUT_FORMAT = """```markdown
# 会议纪要

## 基本信息
- 会议时间: YYYY-MM-DD HH:MM
- 参会人员: xxx, xxx, xxx
- 会议主题: [简短描述]

---

## 讨论议题

### 1. 议题名称
- **负责人**: xxx
- **进度/状态**: xxx
- **关键点**: xxx

### 2. 议题名称
- **负责人**: xxx
- **进度/状态**: xxx
- **关键点**: xxx

---

## 行动项 (Action Items)

| 序号 | 负责人 | 任务描述 | 截止时间 | 优先级 | 状态 |
|:----:|:------:|----------|----------|:------:|:----:|
| 1 | 张三 | xxx | 2026-03-20 | 🔴 高 | ⏳ 待完成 |
| 2 | 李四 | xxx | 2026-03-18 | 🟡 中 | ⏳ 待完成 |

---

## 会议总结

用2-3句话总结会议核心结论和下一步行动。
```"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
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

        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

        logger.info(f"初始化纪要生成器: {self.model}")

    @measure_time
    @retry_on_error(max_retries=3, delay=1.0)
    def generate(
        self,
        transcript: str,
        reference_date: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 3000
    ) -> str:
        """
        从会议转录文本生成结构化纪要

        Args:
            transcript: 会议转录文本
            reference_date: 参考日期（用于解析相对时间），格式 YYYY-MM-DD
            temperature: 采样温度 (0-1)
            max_tokens: 最大输出token数

        Returns:
            Markdown格式的会议纪要
        """
        if not transcript or not transcript.strip():
            raise ValueError("转录文本不能为空")

        logger.info(f"生成会议纪要: {len(transcript)} 字符")

        # 构建提示词
        prompt = self._build_prompt(transcript, reference_date)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            usage = response.usage

            logger.info(
                f"纪要生成完成: {len(content)} 字符 "
                f"(输入: {usage.prompt_tokens} tokens, "
                f"输出: {usage.completion_tokens} tokens)"
            )

            # 清理输出格式
            content = self._clean_output(content)

            return content

        except Exception as e:
            logger.error(f"生成纪要失败: {e}")
            return self._fallback_format(transcript)

    def _build_prompt(self, transcript: str, reference_date: Optional[str]) -> str:
        """构建提示词"""
        ref_date = reference_date or datetime.now().strftime('%Y-%m-%d')

        return f"""请将以下会议转录文本转换为结构化的会议纪要。

要求：
1. 提取参会人员列表
2. 总结主要讨论议题（每个议题用一句话概括）
3. **重点提取行动项**：谁(Who) + 做什么(What) + 截止时间(When)
4. 识别会议中的关键决策
5. 使用Markdown格式输出
6. 如果会议中有明确的时间点（如"下周三"），请转换为具体日期（假设今天是 {ref_date}）

输出格式参考：
{self.DEFAULT_OUTPUT_FORMAT}

以下是会议转录文本：
---
{truncate(transcript, max_length=8000)}
---

请生成会议纪要："""

    def _clean_output(self, content: str) -> str:
        """清理LLM输出，去除多余的代码块标记"""
        content = content.strip()

        # 去除开头的代码块标记
        if content.startswith("```markdown"):
            content = content[11:].lstrip()
        elif content.startswith("```"):
            content = content[3:].lstrip()

        # 去除结尾的代码块标记
        if content.endswith("```"):
            content = content[:-3].rstrip()

        return content

    def _fallback_format(self, transcript: str) -> str:
        """降级格式化（API失败时的备用方案）"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        return f"""# 会议纪要

## 基本信息
- **生成时间**: {timestamp}

---

## 原始转录

{truncate(transcript, max_length=2000)}

---

*注: 由于API错误，仅提供原始转录文本。请检查API配置后重试。*

*生成工具: MeetingMind*
"""

    def extract_action_items(self, minutes: str) -> list[Dict[str, str]]:
        """
        从纪要中提取行动项

        Args:
            minutes: 会议纪要文本

        Returns:
            行动项列表
        """
        import re

        items = []

        # 匹配表格行
        table_pattern = r'\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|'
        matches = re.findall(table_pattern, minutes)

        for match in matches:
            items.append({
                'seq': match[0].strip(),
                'owner': match[1].strip(),
                'task': match[2].strip(),
                'deadline': match[3].strip()
            })

        logger.debug(f"提取到 {len(items)} 个行动项")
        return items

    def extract_participants(self, minutes: str) -> list[str]:
        """
        从纪要中提取参会人员

        Args:
            minutes: 会议纪要文本

        Returns:
            参会人员列表
        """
        import re

        # 查找参会人员行
        pattern = r'参会人员[：:]\s*([^\n]+)'
        match = re.search(pattern, minutes)

        if match:
            # 分割人名（支持中文和英文逗号）
            names = re.split(r'[,，、\s]+', match.group(1))
            return [name.strip() for name in names if name.strip()]

        return []


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试纪要生成器
    print("测试纪要生成器...")

    test_transcript = """张三: 大家好，今天我们讨论一下Q2的产品规划。
李四: 我先说一下技术进度。后端API已经开发完成80%，预计下周可以联调。
王五: 前端进度稍微滞后，目前完成了60%。
张三: 那我们来明确一下行动项。王五负责跟进设计部原型，DDL是本周五。
李四: 收到。"""

    try:
        summarizer = MeetingSummarizer()
        print(f"✅ 纪要生成器初始化成功")
    except ValueError as e:
        print(f"⚠️ {e}")
