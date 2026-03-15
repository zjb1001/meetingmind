#!/usr/bin/env python3
"""
MeetingMind 测试运行器
═══════════════════════════════════════════════════════════════
运行所有测试用例并生成报告
═══════════════════════════════════════════════════════════════
"""

import unittest
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_tests(verbosity=2, pattern=None):
    """
    运行所有测试

    Args:
        verbosity: 输出详细程度 (0-2)
        pattern: 测试文件匹配模式

    Returns:
        测试结果
    """
    # 发现测试
    loader = unittest.TestLoader()

    if pattern:
        tests = loader.discover('tests', pattern=pattern)
    else:
        tests = loader.discover('tests')

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(tests)

    # 返回是否全部通过
    return result.wasSuccessful()


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='MeetingMind 测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_tests.py              # 运行所有测试
  python run_tests.py -v           # 详细输出
  python run_tests.py test_config  # 只运行配置测试
  python run_tests.py -q           # 安静模式
        """
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='安静模式'
    )

    parser.add_argument(
        'pattern',
        nargs='?',
        help='测试文件模式 (如: test_config.py)'
    )

    args = parser.parse_args()

    # 确定详细程度
    if args.verbose:
        verbosity = 2
    elif args.quiet:
        verbosity = 0
    else:
        verbosity = 1

    # 运行测试
    print("=" * 70)
    print("MeetingMind 测试套件")
    print("=" * 70)
    print()

    success = run_tests(verbosity=verbosity, pattern=args.pattern)

    print()
    print("=" * 70)

    if success:
        print("✅ 所有测试通过!")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
