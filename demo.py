#!/usr/bin/env python3
"""
Google Scholar 引用爬虫 - 完整示例
演示从爬取到可视化的完整工作流程
"""

import sys
import os
from datetime import datetime
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json
from papertracer_config import Config, DEMO_CONFIG

def ensure_output_directory():
    """确保输出目录存在"""
    created = Config.ensure_output_directory()
    if created:
        print(f"   ✓ 创建输出目录: {Config.OUTPUT_DIR}/")
    else:
        print(f"   ✓ 输出目录已存在: {Config.OUTPUT_DIR}/")
    return Config.OUTPUT_DIR

def demo_workflow():
    """演示完整的工作流程"""
    print("🕷️  Google Scholar 引用爬虫 - 完整演示")
    print("=" * 60)
    
    # 步骤0: 准备输出目录
    print("📁 步骤0: 准备输出目录...")
    output_dir = ensure_output_directory()
    
    # 生成带时间戳的文件名前缀
    file_prefix = Config.get_timestamped_filename(extension="").rstrip('.')
    
    # 步骤1: 创建爬虫实例
    print("🔧 步骤1: 配置爬虫...")
    config = DEMO_CONFIG
    crawler = GoogleScholarCrawler(
        max_depth=config['max_depth'],
        max_papers_per_level=config['max_papers_per_level'],
        delay_range=config['delay_range']
    )
    print("   ✓ 爬虫配置完成")
    
    # 步骤2: 设置起始URL
    print("\n📋 步骤2: 设置起始URL...")
    start_url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"
    print(f"   ✓ 起始URL: {start_url}")
    
    # 步骤3: 爬取引用树
    print("\n🚀 步骤3: 开始爬取引用树...")
    print("   (这可能需要几分钟时间，请耐心等待...)")
    
    try:
        citation_tree = crawler.build_citation_tree(start_url)
        
        if not citation_tree:
            print("   ❌ 无法构建引用树")
            return False
        
        print("   ✅ 引用树构建成功!")
        
        # 步骤4: 显示结果
        print("\n📊 步骤4: 显示爬取结果...")
        print("-" * 60)
        print_citation_tree(citation_tree)
        
        # 步骤5: 保存数据
        print("\n💾 步骤5: 保存数据...")
        json_filename = Config.get_timestamped_filename(
            prefix="demo",
            suffix="citation_tree",
            extension="json"
        )
        json_path = Config.get_output_path(json_filename)
        save_tree_to_json(citation_tree, json_path)
        print(f"   ✓ 数据已保存到: {json_path}")
        
        # 步骤6: 创建可视化（如果可能）
        print("\n🎨 步骤6: 创建可视化图表...")
        try:
            from visualize_tree import CitationTreeVisualizer
            
            visualizer = CitationTreeVisualizer(json_path)
            
            # 创建简单的网络图
            print("   正在创建网络图...")
            simple_filename = Config.get_timestamped_filename(
                prefix="demo",
                suffix="simple",
                extension="png"
            )
            simple_path = Config.get_output_path(simple_filename)
            visualizer.create_simple_visualization(simple_path, figsize=config['figsize'])
            
            # 创建统计图表
            print("   正在创建统计图表...")
            stats_filename = Config.get_timestamped_filename(
                prefix="demo",
                suffix="stats",
                extension="png"
            )
            stats_path = Config.get_output_path(stats_filename)
            visualizer.create_statistics_plot(stats_path)
            
            print("   ✅ 可视化图表创建完成!")
            print(f"   📁 输出文件:")
            print(f"      - {simple_path} (网络图)")
            print(f"      - {stats_path} (统计图)")
            
        except ImportError as e:
            print(f"   ⚠️  可视化功能需要额外依赖: {e}")
            print("   💡 可以运行: pip install matplotlib networkx")
        except Exception as e:
            print(f"   ⚠️  可视化过程中出现问题: {e}")
        
        # 步骤7: 显示统计信息
        print("\n📈 步骤7: 统计信息...")
        
        def count_nodes(node):
            count = 1
            for child in node.children:
                count += count_nodes(child)
            return count
        
        def collect_papers(node):
            papers = [node.paper]
            for child in node.children:
                papers.extend(collect_papers(child))
            return papers
        
        total_papers = count_nodes(citation_tree)
        all_papers = collect_papers(citation_tree)
        
        # 计算统计信息
        citation_counts = [p.citation_count for p in all_papers if p.citation_count > 0]
        years = [int(p.year) for p in all_papers if p.year.isdigit()]
        
        print(f"   📊 总论文数: {total_papers}")
        print(f"   🌳 树的最大深度: {crawler.max_depth}")
        print(f"   👥 根节点直接子节点: {len(citation_tree.children)}")
        
        if citation_counts:
            print(f"   📈 平均引用次数: {sum(citation_counts)/len(citation_counts):.1f}")
            print(f"   🔝 最高引用次数: {max(citation_counts)}")
        
        if years:
            print(f"   📅 发表年份范围: {min(years)} - {max(years)}")
        
        # 步骤8: 展示如何使用数据
        print("\n🛠️  步骤8: 如何使用生成的数据...")
        print("   1. JSON文件可以导入到其他程序进行进一步分析")
        print("   2. 所有输出文件都保存在 output/ 目录中，便于管理")
        print("   3. 可以使用以下命令创建更多可视化:")
        print(f"      python visualize_tree.py {json_filename} --type all")
        print("   4. 数据结构说明:")
        print("      - 每个节点包含论文的完整信息")
        print("      - 树形结构保持了引用的层次关系")
        print("      - 可以递归遍历整个引用网络")
        print("   5. 文件命名包含时间戳，避免覆盖之前的结果")
        
        print("\n✅ 演示完成!")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  用户中断操作")
        return False
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        return False

def show_usage():
    """显示使用说明"""
    print("🕷️  Google Scholar 引用爬虫工具套件")
    print("=" * 60)
    print()
    print("📁 项目文件:")
    print("   papertrace.py      - 主爬虫模块")
    print("   test_crawler.py    - 测试和配置工具")
    print("   visualize_tree.py  - 可视化工具")
    print("   demo.py           - 完整演示脚本")
    print("   requirements.txt  - 依赖列表")
    print("   README.md         - 详细说明文档")
    print("   output/           - 输出目录（自动创建）")
    print()
    print("🚀 快速开始:")
    print("   1. 安装依赖:     pip install -r requirements.txt")
    print("   2. 运行演示:     python demo.py --demo")
    print("   3. 交互测试:     python test_crawler.py --interactive")
    print("   4. 创建可视化:   python visualize_tree.py output/<json_file>")
    print()
    print("⚙️  使用选项:")
    print("   python demo.py --demo    # 运行完整演示")
    print("   python demo.py --help    # 显示此帮助信息")
    print()
    print("💡 提示:")
    print("   - 首次使用建议先运行演示来了解功能")
    print("   - 可以修改 papertrace.py 中的参数来自定义爬取行为")
    print("   - 所有输出文件（JSON和图表）都会保存在 output/ 目录中")
    print("   - 生成的JSON文件可以重复用于创建不同类型的可视化")
    print("   - 文件名包含时间戳，避免覆盖之前的结果")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--demo":
            demo_workflow()
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            show_usage()
        else:
            print(f"❌ 未知参数: {sys.argv[1]}")
            print("使用 --help 查看帮助信息")
    else:
        show_usage()
