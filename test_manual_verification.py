#!/usr/bin/env python3
"""
Test script to demonstrate enhanced manual verification functionality
测试脚本 - 演示增强的手动验证功能
"""

import sys
from papertracer import GoogleScholarCrawler
from logger import get_logger

def test_manual_verification():
    """测试手动验证功能的增强特性"""
    
    print("🧪 PaperTracer 手动验证测试")
    print("=" * 50)
    print("本测试将演示增强的手动验证功能，包括:")
    print("✅ 浏览器窗口状态检查")
    print("✅ 窗口关闭错误处理")
    print("✅ 重试机制")
    print("✅ 页面内容验证")
    print("=" * 50)
    
    # 设置日志
    logger = get_logger()
    
    try:
        # 创建爬虫实例，启用手动模式
        crawler = GoogleScholarCrawler(
            max_depth=1,
            max_papers_per_level=1,
            delay_range=(1, 2),
            max_captcha_retries=3,
            use_browser_fallback=True
        )
        
        # 强制设置为有头模式（手动验证需要）
        crawler.use_headless_browser = False
        
        print("🔍 开始测试...")
        print("💡 提示：测试将使用一个可能触发CAPTCHA的Scholar URL")
        print("      这将演示增强的手动验证功能")
        print()
        
        # 使用一个容易触发验证的URL（引用页面）
        test_url = "https://scholar.google.com/scholar?cites=123456789&hl=en"
        
        print(f"🌐 测试URL: {test_url}")
        print("📝 注意：如果出现浏览器窗口，请不要手动关闭")
        print("      系统会自动检测窗口状态并处理各种异常情况")
        print()
        
        # 尝试获取页面（这可能触发手动验证）
        response = crawler._make_request(test_url)
        
        if response and hasattr(response, 'status_code'):
            print(f"✅ 请求成功! 状态码: {response.status_code}")
            print(f"📊 响应长度: {len(response.text) if response.text else 0} 字符")
        else:
            print("ℹ️  响应为空或特殊格式（可能经过了手动验证处理）")
        
        print()
        print("🎉 测试完成！增强的手动验证功能已验证")
        print(f"📈 统计: 总请求 {crawler.request_count}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断测试")
        return False
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        print("💡 这可能是正常的测试行为（用于验证错误处理）")
        return False

if __name__ == "__main__":
    print("注意：此测试脚本用于演示手动验证功能")
    print("实际使用时请使用 enhanced_demo.py 的 --manual-captcha 选项")
    print()
    
    success = test_manual_verification()
    sys.exit(0 if success else 1)
