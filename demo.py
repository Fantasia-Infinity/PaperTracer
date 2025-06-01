#!/usr/bin/env python3
"""
PaperTracer 增强演示脚本
包含配置管理、日志记录和错误处理的完整演示
"""

import sys
import os
import argparse
from papertracer_config import Config, DEMO_CONFIG, PRODUCTION_CONFIG, QUICK_TEST_CONFIG
from logger import get_logger
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json

def setup_argument_parser():
    """设置命令行参数解析"""
    parser = argparse.ArgumentParser(
        description='PaperTracer 增强演示 - Google Scholar 引用爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python demo.py --url "https://scholar.google.com/..."
  python demo.py --config production --depth 3
  python demo.py --config quick --no-visualization
        """
    )
    
    parser.add_argument(
        '--url', '-u',
        type=str,
        default="https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en",
        help='起始URL (默认: 预设示例URL)'
    )
    
    parser.add_argument(
        '--config', '-c',
        choices=['demo', 'production', 'quick'],
        default='demo',
        help='使用预设配置 (默认: demo)'
    )
    
    parser.add_argument(
        '--depth', '-d',
        type=int,
        help='递归深度 (覆盖配置文件设置)'
    )
    
    parser.add_argument(
        '--max-papers', '-m',
        type=int,
        help='每层最大论文数 (覆盖配置文件设置)'
    )
    
    parser.add_argument(
        '--output-prefix', '-p',
        type=str,
        default='demo',
        help='输出文件前缀 (默认: demo)'
    )
    
    parser.add_argument(
        '--no-html',
        action='store_true',
        help='跳过HTML交互式可视化生成'
    )
    
    parser.add_argument(
        '--no-visualization',
        action='store_true',
        help='跳过所有可视化生成'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='禁用浏览器fallback模式 (当CAPTCHA出现时)'
    )
    
    parser.add_argument(
        '--captcha-retries',
        type=int,
        default=3,
        help='CAPTCHA重试次数 (默认: 3)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    return parser

def get_config(config_name, args):
    """获取配置参数"""
    config_map = {
        'demo': DEMO_CONFIG,
        'production': PRODUCTION_CONFIG,
        'quick': QUICK_TEST_CONFIG
    }
    
    config = config_map[config_name].copy()
    
    # 命令行参数覆盖配置文件
    if args.depth is not None:
        config['max_depth'] = args.depth
    if args.max_papers is not None:
        config['max_papers_per_level'] = args.max_papers
    
    return config

def run_enhanced_demo():
    """运行增强演示"""
    # 解析命令行参数
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # 获取日志器
    logger = get_logger()
    
    # 设置日志级别
    if args.verbose:
        logger.logger.setLevel(10)  # DEBUG
    
    logger.info("🕷️  PaperTracer 增强演示开始")
    logger.info("=" * 60)
    
    try:
        # 准备输出目录
        logger.info("📁 准备输出目录...")
        Config.ensure_output_directory()
        logger.info(f"   ✓ 输出目录: {Config.OUTPUT_DIR}/")
        
        # 获取配置
        config = get_config(args.config, args)
        logger.info(f"🔧 使用配置: {args.config}")
        logger.info(f"   - 递归深度: {config['max_depth']}")
        logger.info(f"   - 每层论文数: {config['max_papers_per_level']}")
        logger.info(f"   - 延迟范围: {config['delay_range']} 秒")
        logger.info(f"   - CAPTCHA重试次数: {args.captcha_retries}")
        logger.info(f"   - 浏览器fallback模式: {'禁用' if args.no_browser else '启用'}")
        
        # 创建爬虫实例
        logger.info("🚀 初始化爬虫...")
        crawler = GoogleScholarCrawler(
            max_depth=config['max_depth'],
            max_papers_per_level=config['max_papers_per_level'],
            delay_range=config['delay_range'],
            max_captcha_retries=args.captcha_retries,
            use_browser_fallback=not args.no_browser
        )
        
        # 显示起始URL
        logger.info(f"📋 起始URL: {args.url}")
        
        # 爬取引用树
        logger.info("🔍 开始爬取引用树...")
        logger.info("   (根据配置，这可能需要几分钟时间...)")
        
        citation_tree = crawler.build_citation_tree(args.url)
        
        if not citation_tree:
            logger.error("❌ 无法构建引用树")
            return False
        
        logger.info("✅ 引用树构建成功!")
        
        # 显示结果
        logger.info("📊 显示爬取结果...")
        print("-" * 60)
        print_citation_tree(citation_tree)
        
        # 保存数据
        logger.info("💾 保存数据...")
        json_filename = Config.get_timestamped_filename(
            prefix=args.output_prefix,
            suffix="citation_tree",
            extension="json"
        )
        json_path = Config.get_output_path(json_filename)
        save_tree_to_json(citation_tree, json_path)
        logger.info(f"   ✓ 数据已保存到: {json_path}")
        
        # 创建可视化
        if not args.no_visualization:
            logger.info("🎨 创建可视化图表...")
            try:
                from visualize_tree import CitationTreeVisualizer
                
                visualizer = CitationTreeVisualizer(json_path)
                
                # 简单网络图
                logger.info("   正在创建网络图...")
                simple_filename = Config.get_timestamped_filename(
                    prefix=args.output_prefix,
                    suffix="simple",
                    extension="png"
                )
                simple_path = Config.get_output_path(simple_filename)
                visualizer.create_simple_visualization(
                    simple_path, 
                    figsize=config['figsize']
                )
                
                # 统计图表
                logger.info("   正在创建统计图表...")
                stats_filename = Config.get_timestamped_filename(
                    prefix=args.output_prefix,
                    suffix="stats",
                    extension="png"
                )
                stats_path = Config.get_output_path(stats_filename)
                visualizer.create_statistics_plot(stats_path)
                
                # 创建交互式HTML可视化
                if not args.no_html:
                    logger.info("   正在创建交互式HTML可视化...")
                    try:
                        from html_visualizer import InteractiveHTMLVisualizer
                        
                        html_visualizer = InteractiveHTMLVisualizer(json_path)
                        html_filename = Config.get_timestamped_filename(
                            prefix=args.output_prefix,
                            suffix="interactive",
                            extension="html"
                        )
                        html_path = Config.get_output_path(html_filename)
                        html_visualizer.create_interactive_html(html_path)
                        
                        logger.info("✅ 可视化图表创建完成!")
                        logger.info(f"📁 输出文件:")
                        logger.info(f"   - {json_path} (数据)")
                        logger.info(f"   - {simple_path} (网络图)")
                        logger.info(f"   - {stats_path} (统计图)")
                        logger.info(f"   - {html_path} (交互式网页)")
                        logger.info(f"🌐 在浏览器中打开 {html_path} 查看交互式可视化")
                        
                    except Exception as html_e:
                        logger.warning(f"⚠️  HTML可视化创建失败: {html_e}")
                        logger.info("✅ 静态可视化图表创建完成!")
                        logger.info(f"📁 输出文件:")
                        logger.info(f"   - {json_path} (数据)")
                        logger.info(f"   - {simple_path} (网络图)")
                        logger.info(f"   - {stats_path} (统计图)")
                else:
                    logger.info("✅ 静态可视化图表创建完成!")
                    logger.info(f"📁 输出文件:")
                    logger.info(f"   - {json_path} (数据)")
                    logger.info(f"   - {simple_path} (网络图)")
                    logger.info(f"   - {stats_path} (统计图)")
                    logger.info("⏭️  跳过HTML可视化 (使用了 --no-html)")
                
            except ImportError as e:
                logger.warning(f"⚠️  可视化功能需要额外依赖: {e}")
                logger.info("💡 可以运行: pip install matplotlib networkx")
            except Exception as e:
                logger.error(f"⚠️  可视化过程中出现问题: {e}")
        else:
            logger.info("⏭️  跳过所有可视化 (使用了 --no-visualization)")
            logger.info(f"📁 输出文件:")
            logger.info(f"   - {json_path} (数据)")
            logger.info("💡 可以稍后使用 python html_visualizer.py 创建可视化")
        
        # 显示完成信息
        logger.info("🎉 演示完成!")
        logger.info("📊 可以使用以下命令查看输出文件:")
        logger.info("   python clean_output.py list")
        
        return True
        
    except KeyboardInterrupt:
        logger.warning("⚠️  用户中断操作")
        return False
    except Exception as e:
        logger.error(f"❌ 演示过程中出现错误: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_enhanced_demo()
    sys.exit(0 if success else 1)
