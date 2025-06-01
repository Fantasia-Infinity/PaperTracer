#!/usr/bin/env python3
"""
测试 Google Scholar 引用爬虫
用法示例和简单测试
"""

from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json
import sys

def test_crawler_basic():
    """基本功能测试"""
    print("🧪 开始基本功能测试...")
    
    # 使用较小的参数进行测试
    crawler = GoogleScholarCrawler(
        max_depth=2,  # 较小的深度
        max_papers_per_level=3,  # 较少的论文数
        delay_range=(0.5, 1.5)  # 较短的延迟
    )
    
    # 测试URL
    test_url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"
    
    print(f"📋 测试URL: {test_url}")
    print(f"🔧 配置: 深度={crawler.max_depth}, 每层论文数={crawler.max_papers_per_level}")
    print("-" * 60)
    
    try:
        # 构建引用树
        citation_tree = crawler.build_citation_tree(test_url)
        
        if citation_tree:
            print("\n✅ 测试成功！引用树构建完成")
            print("=" * 60)
            
            # 打印树结构
            print_citation_tree(citation_tree)
            
            # 保存结果
            save_tree_to_json(citation_tree, "test_citation_tree.json")
            
            # 统计信息
            def count_nodes(node):
                count = 1
                for child in node.children:
                    count += count_nodes(child)
                return count
            
            total_papers = count_nodes(citation_tree)
            print(f"\n📊 测试结果统计:")
            print(f"   ✓ 总论文数: {total_papers}")
            print(f"   ✓ 树的最大深度: {crawler.max_depth}")
            print(f"   ✓ 根节点直接子节点: {len(citation_tree.children)}")
            print(f"   ✓ 结果已保存到: test_citation_tree.json")
            
            return True
            
        else:
            print("❌ 测试失败：无法构建引用树")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def interactive_test():
    """交互式测试"""
    print("\n🎯 交互式测试模式")
    print("请输入要爬取的Google Scholar链接（直接回车使用默认链接）:")
    
    url = input().strip()
    if not url:
        url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"
        print(f"使用默认链接: {url}")
    
    print("\n请配置爬虫参数（直接回车使用默认值）:")
    
    # 获取深度
    depth_input = input("最大递归深度 (默认2): ").strip()
    max_depth = int(depth_input) if depth_input.isdigit() else 2
    
    # 获取每层论文数
    papers_input = input("每层最多论文数 (默认5): ").strip()
    max_papers = int(papers_input) if papers_input.isdigit() else 5
    
    # 获取延迟时间
    delay_input = input("请求间隔秒数 (默认1-2): ").strip()
    delay = float(delay_input) if delay_input.replace('.', '').isdigit() else 1.5
    
    print(f"\n🔧 配置确认:")
    print(f"   URL: {url}")
    print(f"   最大深度: {max_depth}")
    print(f"   每层论文数: {max_papers}")
    print(f"   请求间隔: {delay}秒")
    print(f"   预估运行时间: {delay * max_papers * (max_papers ** max_depth) / 60:.1f} 分钟")
    
    confirm = input("\n确认开始爬取？(y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消操作")
        return
    
    # 创建爬虫实例
    crawler = GoogleScholarCrawler(
        max_depth=max_depth,
        max_papers_per_level=max_papers,
        delay_range=(delay, delay + 0.5)
    )
    
    try:
        print("\n🚀 开始爬取...")
        citation_tree = crawler.build_citation_tree(url)
        
        if citation_tree:
            print("\n✅ 爬取完成！")
            print("=" * 60)
            
            # 显示结果
            print_citation_tree(citation_tree)
            
            # 保存结果
            filename = f"citation_tree_{int(time.time())}.json"
            save_tree_to_json(citation_tree, filename)
            
            print(f"\n💾 结果已保存到: {filename}")
            
        else:
            print("❌ 爬取失败")
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断操作")
    except Exception as e:
        print(f"❌ 爬取过程中发生错误: {e}")

def main():
    """主函数"""
    print("🕷️  Google Scholar 引用爬虫测试工具")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            # 运行基本测试
            success = test_crawler_basic()
            sys.exit(0 if success else 1)
        elif sys.argv[1] == "--interactive":
            # 运行交互式测试
            interactive_test()
            return
    
    # 默认显示帮助信息
    print("使用方法:")
    print("  python test_crawler.py --test        # 运行基本功能测试")
    print("  python test_crawler.py --interactive # 交互式配置和测试")
    print("  python test_crawler.py               # 显示此帮助信息")
    print()
    print("注意事项:")
    print("  1. 请遵守Google Scholar的使用条款")
    print("  2. 避免过于频繁的请求，建议设置合适的延迟时间")
    print("  3. 大规模爬取可能需要较长时间，请耐心等待")
    print("  4. 如果遇到反爬措施，可以尝试增加延迟时间")

if __name__ == "__main__":
    import time
    main()
