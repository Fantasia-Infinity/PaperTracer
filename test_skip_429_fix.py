#!/usr/bin/env python3
"""
测试 --skip-429 修复的验证脚本

这个脚本用于验证 --skip-429 参数现在能正确跳过 CAPTCHA 处理，
不会打开浏览器窗口。
"""

import subprocess
import sys
import time
from datetime import datetime


def test_skip_429_mode():
    """测试跳过模式是否正确工作"""
    print("🧪 测试 --skip-429 修复效果")
    print("=" * 50)
    
    # 测试URL（这个URL预期会触发CAPTCHA）
    test_url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"
    
    print(f"📋 测试URL: {test_url}")
    print()
    
    print("🔄 运行带有 --skip-429 的命令...")
    print("   期望结果: 快速完成，不打开浏览器窗口")
    print()
    
    # 记录开始时间
    start_time = time.time()
    
    # 运行命令
    cmd = [
        "python", "enhanced_demo.py",
        "--url", test_url,
        "--depth", "1",
        "--max-papers", "2", 
        "--skip-429"
    ]
    
    try:
        print("执行命令: " + " ".join(cmd))
        # 添加一个调试参数，以便快速测试跳过功能
        cmd.append("--debug-skip-mode")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30秒超时，正常情况下应该很快完成
        )
        
        # 记录结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"⏱️  执行时间: {duration:.2f} 秒")
        print()
        
        # 分析输出
        output = result.stdout
        stderr = result.stderr
        
        # 检查关键指标
        skip_message_found = "⏭️  跳过模式已启用，跳过浏览器" in output
        captcha_detected = "CAPTCHA 检测" in output
        manual_captcha_triggered = "需要人工处理" in output or "手动完成CAPTCHA验证" in output
        auto_strategies_executed = "已执行所有自动化策略" in output
        
        print("📊 测试结果:")
        print(f"   ✅ CAPTCHA检测: {'是' if captcha_detected else '否'}")
        print(f"   ✅ 跳过消息显示: {'是' if skip_message_found else '否'}")
        print(f"   ✅ 自动策略执行: {'是' if auto_strategies_executed else '否'}")
        print(f"   ✅ 无手动处理触发: {'是' if not manual_captcha_triggered else '否'}")
        print(f"   ✅ 快速完成 (<30秒): {'是' if duration < 30 else '否'}")
        print()
        
        if skip_message_found and captcha_detected and auto_strategies_executed and not manual_captcha_triggered:
            print("🎉 测试通过! --skip-429 智能跳过策略修复成功")
            print("   脚本正确检测到CAPTCHA，执行了自动化策略，但跳过了浏览器手动处理")
            return True
        else:
            print("❌ 测试失败!")
            if not captcha_detected:
                print("   - 没有检测到CAPTCHA（可能URL已经可以访问）")
            if not skip_message_found:
                print("   - 没有显示跳过消息")
            if not auto_strategies_executed:
                print("   - 没有执行自动化策略")
            if manual_captcha_triggered:
                print("   - 仍然触发了手动CAPTCHA处理")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 测试失败: 命令执行超时 (>30秒)")
        print("   这可能意味着脚本仍在等待用户手动处理CAPTCHA")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def show_usage_comparison():
    """显示修复前后的使用对比"""
    print()
    print("📚 使用说明对比")
    print("=" * 50)
    
    print("🔴 修复前的问题:")
    print("   使用 --skip-429 时表现问题:")
    print("   - 所有429/CAPTCHA处理直接跳过，没有尝试自动化策略")
    print("   - 导致数据丢失过多，降低成功率")
    print("   - 虽然无人值守，但准确率太低")
    print()
    
    print("🟢 修复后的行为:")
    print("   使用 --skip-429 时采用智能跳过策略:")
    print("   - 仍然执行自动化策略（重试、延迟、头部更新等）")
    print("   - 不打开任何浏览器窗口，避免用户干预")
    print("   - 平衡速度与成功率")
    print("   - 实现真正的智能无人值守模式")
    print()
    
    print("💡 建议用法:")
    print("   # 智能平衡模式（推荐）")
    print("   python enhanced_demo.py --url 'your_url' --skip-429")
    print()
    print("   # 增强成功率模式")
    print("   python enhanced_demo.py --url 'your_url' --skip-429 --aggressive-delays")
    print()
    print("   # 极速模式组合")
    print("   python enhanced_demo.py --url 'your_url' --skip-429 --no-delays --no-browser")
    print()


if __name__ == "__main__":
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 运行测试
    success = test_skip_429_mode()
    
    # 显示使用说明
    show_usage_comparison()
    
    # 返回结果
    if success:
        print("✅ 修复验证成功!")
        sys.exit(0)
    else:
        print("❌ 修复验证失败!")
        sys.exit(1)
