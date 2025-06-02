#!/usr/bin/env python3
"""
PaperTracer 增强演示脚本
包含会话恢复、智能重试和高级错误处理的完整演示
"""

import sys
import os
import argparse
import json
from pathlib import Path
from papertracer_config import Config, DEMO_CONFIG, PRODUCTION_CONFIG, QUICK_TEST_CONFIG
from logger import get_logger
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json

def setup_enhanced_argument_parser():
    """设置增强版命令行参数解析"""
    parser = argparse.ArgumentParser(
        description='PaperTracer 增强演示 - 支持会话恢复的Google Scholar引用爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
增强功能:
  - 自动会话状态保存和恢复
  - 智能429错误处理和退避策略
  - 增强的反爬虫检测规避
  - 更好的Chrome驱动兼容性

示例用法:
  python enhanced_demo.py --url "https://scholar.google.com/..."
  python enhanced_demo.py --resume session_20240602_123456
  python enhanced_demo.py --config production --save-session
  python enhanced_demo.py --manual-captcha --no-delays
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
        '--save-session',
        action='store_true',
        help='自动保存会话状态以供恢复'
    )
    
    parser.add_argument(
        '--resume',
        type=str,
        help='从指定会话ID恢复 (例如: session_20240602_123456)'
    )
    
    parser.add_argument(
        '--session-interval',
        type=int,
        default=50,
        help='每隔多少个请求保存一次会话状态 (默认: 50)'
    )
    
    parser.add_argument(
        '--aggressive-delays',
        action='store_true',
        help='使用更激进的延迟策略以避免429错误'
    )
    
    parser.add_argument(
        '--output-prefix', '-p',
        type=str,
        default='enhanced_demo',
        help='输出文件前缀 (默认: enhanced_demo)'
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
        help='禁用浏览器fallback模式'
    )
    
    parser.add_argument(
        '--captcha-retries',
        type=int,
        default=5,
        help='CAPTCHA重试次数 (默认: 5)'
    )
    
    parser.add_argument(
        '--manual-captcha',
        action='store_true',
        help='启用手动CAPTCHA处理模式（禁用无头浏览器）'
    )
    
    parser.add_argument(
        '--no-delays',
        action='store_true',
        help='禁用所有延迟策略（谨慎使用，可能导致更多429错误）'
    )
    
    parser.add_argument(
        '--skip-429',
        action='store_true',
        help='遇到429错误时直接跳过，不进行任何修复和重试（极速模式）'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    return parser

def get_enhanced_config(config_name, args):
    """获取增强配置参数"""
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
    
    # 如果使用激进延迟策略，增加延迟范围
    if args.aggressive_delays:
        current_min, current_max = config['delay_range']
        config['delay_range'] = (current_min * 1.5, current_max * 2.0)
    
    # 如果禁用延迟策略，设置极小的延迟
    if args.no_delays:
        from logger import get_logger
        logger = get_logger()
        config['delay_range'] = (0.1, 0.3)
        logger.warning("⚠️  延迟策略已禁用，这可能导致更多429错误！")
    
    return config

def create_session_manager(session_dir, args):
    """创建会话管理器"""
    class SessionManager:
        def __init__(self, session_dir, save_interval=50):
            self.session_dir = Path(session_dir)
            self.save_interval = save_interval
            self.session_file = self.session_dir / "session_state.json"
            self.request_counter = 0
            
        def should_save(self, crawler):
            """检查是否应该保存会话状态"""
            self.request_counter += 1
            return self.request_counter % self.save_interval == 0
            
        def save_if_needed(self, crawler):
            """如果需要则保存会话状态"""
            if self.should_save(crawler):
                crawler.save_session_state(str(self.session_file))
                return True
            return False
            
        def force_save(self, crawler):
            """强制保存会话状态"""
            crawler.save_session_state(str(self.session_file))
            
        def load_session(self, crawler):
            """加载会话状态"""
            if self.session_file.exists():
                return crawler.load_session_state(str(self.session_file))
            return False
    
    return SessionManager(session_dir, args.session_interval)

def run_enhanced_demo():
    """运行增强演示"""
    # 解析命令行参数
    parser = setup_enhanced_argument_parser()
    args = parser.parse_args()
    
    # 获取日志器
    logger = get_logger()
    
    # 设置日志级别
    if args.verbose:
        logger.logger.setLevel(10)  # DEBUG
    
    logger.info("🚀 PaperTracer 增强演示开始")
    logger.info("=" * 70)
    
    try:
        # 准备输出目录和会话目录
        logger.info("📁 准备输出目录...")
        Config.ensure_output_directory()
        
        # 创建本次爬取的会话目录
        session_dir = Config.get_timestamped_dirname(args.output_prefix)
        Config.ensure_output_directory(session_dir)
        logger.info(f"   ✓ 主输出目录: {Config.OUTPUT_DIR}/")
        logger.info(f"   ✓ 会话目录: {Config.OUTPUT_DIR}/{session_dir}/")
        
        # 获取配置
        config = get_enhanced_config(args.config, args)
        logger.info(f"🔧 使用增强配置: {args.config}")
        logger.info(f"   - 递归深度: {config['max_depth']}")
        logger.info(f"   - 每层论文数: {config['max_papers_per_level']}")
        logger.info(f"   - 延迟范围: {config['delay_range']} 秒")
        logger.info(f"   - CAPTCHA重试次数: {args.captcha_retries}")
        logger.info(f"   - 浏览器fallback: {'禁用' if args.no_browser else '启用'}")
        logger.info(f"   - 激进延迟策略: {'启用' if args.aggressive_delays else '禁用'}")
        logger.info(f"   - 延迟策略: {'禁用' if args.no_delays else '启用'}")
        logger.info(f"   - 手动CAPTCHA模式: {'启用' if args.manual_captcha else '禁用'}")
        logger.info(f"   - 429跳过模式: {'启用' if args.skip_429 else '禁用'}")
        logger.info(f"   - 会话保存间隔: {args.session_interval} 请求")
        
        # 创建增强爬虫实例
        logger.info("🚀 初始化增强爬虫...")
        
        # 设置无头浏览器模式（如果启用手动CAPTCHA，则使用有头模式）
        use_headless = not args.manual_captcha
        
        crawler = GoogleScholarCrawler(
            max_depth=config['max_depth'],
            max_papers_per_level=config['max_papers_per_level'],
            delay_range=config['delay_range'],
            max_captcha_retries=args.captcha_retries,
            use_browser_fallback=not args.no_browser,
            skip_429_errors=args.skip_429
        )
        
        # 如果启用手动CAPTCHA模式，设置浏览器为有头模式
        if args.manual_captcha:
            crawler.use_headless_browser = False
            logger.info("🎯 手动CAPTCHA模式已启用，浏览器将以有头模式运行")
        
        # 设置会话管理器
        session_manager = None
        if args.save_session or args.resume:
            session_manager = create_session_manager(
                Config.get_output_path('', session_dir), 
                args
            )
            
            # 如果指定了恢复会话
            if args.resume:
                # 尝试加载指定的会话
                resume_session_file = Config.OUTPUT_DIR / args.resume / "session_state.json"
                if resume_session_file.exists():
                    if crawler.load_session_state(str(resume_session_file)):
                        logger.info(f"✅ 成功恢复会话: {args.resume}")
                    else:
                        logger.warning(f"⚠️  恢复会话失败: {args.resume}")
                else:
                    logger.error(f"❌ 会话文件不存在: {resume_session_file}")
                    return False
            
            logger.info("📊 会话管理已启用")
        
        # 显示起始URL
        logger.info(f"📋 起始URL: {args.url}")
        
        # 爬取引用树
        logger.info("🔍 开始爬取引用树...")
        logger.info("   (根据配置，这可能需要几分钟到几十分钟...)")
        
        # 包装build_citation_tree方法以支持会话保存
        original_build_method = crawler.build_citation_tree
        
        def enhanced_build_citation_tree(url, current_depth=0):
            """增强版构建引用树，支持会话保存"""
            result = original_build_method(url, current_depth)
            
            # 在会话管理器中保存状态
            if session_manager and args.save_session:
                if session_manager.save_if_needed(crawler):
                    logger.info("💾 自动保存会话状态")
            
            return result
        
        # 替换方法
        crawler.build_citation_tree = enhanced_build_citation_tree
        
        citation_tree = crawler.build_citation_tree(args.url)
        
        # 最终保存会话状态
        if session_manager and args.save_session:
            session_manager.force_save(crawler)
            logger.info("💾 最终会话状态已保存")
        
        if not citation_tree:
            logger.error("❌ 无法构建引用树")
            return False
        
        logger.info("✅ 引用树构建成功!")
        logger.info(f"📊 最终统计:")
        logger.info(f"   - 总请求数: {crawler.request_count}")
        logger.info(f"   - 已访问URL数: {len(crawler.visited_urls)}")
        logger.info(f"   - 连续429错误次数: {crawler.consecutive_429_count}")
        
        # 显示结果
        logger.info("📊 显示爬取结果...")
        print("-" * 70)
        print_citation_tree(citation_tree)
        
        # 保存数据
        logger.info("💾 保存数据...")
        json_filename = Config.get_timestamped_filename(
            prefix="enhanced_citation_tree",
            suffix="",
            extension="json"
        )
        json_path = Config.get_output_path(json_filename, session_dir)
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
                    prefix="enhanced_simple",
                    suffix="",
                    extension="png"
                )
                simple_path = Config.get_output_path(simple_filename, session_dir)
                visualizer.create_simple_visualization(
                    simple_path, 
                    figsize=config['figsize']
                )
                
                # 统计图表
                logger.info("   正在创建统计图表...")
                stats_filename = Config.get_timestamped_filename(
                    prefix="enhanced_stats",
                    suffix="",
                    extension="png"
                )
                stats_path = Config.get_output_path(stats_filename, session_dir)
                visualizer.create_statistics_plot(stats_path)
                
                # 创建交互式HTML可视化
                if not args.no_html:
                    logger.info("   正在创建交互式HTML可视化...")
                    try:
                        from html_visualizer import InteractiveHTMLVisualizer
                        
                        html_visualizer = InteractiveHTMLVisualizer(json_path)
                        html_filename = Config.get_timestamped_filename(
                            prefix="enhanced_interactive",
                            suffix="",
                            extension="html"
                        )
                        html_path = Config.get_output_path(html_filename, session_dir)
                        html_visualizer.create_interactive_html(html_path)
                        
                        logger.info("✅ 增强可视化图表创建完成!")
                        logger.info(f"📁 输出文件夹: {Config.OUTPUT_DIR}/{session_dir}/")
                        logger.info(f"📄 输出文件:")
                        logger.info(f"   - {os.path.basename(json_path)} (数据)")
                        logger.info(f"   - {os.path.basename(simple_path)} (网络图)")
                        logger.info(f"   - {os.path.basename(stats_path)} (统计图)")
                        logger.info(f"   - {os.path.basename(html_path)} (交互式网页)")
                        if session_manager and args.save_session:
                            logger.info(f"   - session_state.json (会话状态)")
                        logger.info(f"🌐 在浏览器中打开 {html_path} 查看交互式可视化")
                        
                    except Exception as html_e:
                        logger.warning(f"⚠️  HTML可视化创建失败: {html_e}")
                        logger.info("✅ 静态可视化图表创建完成!")
                        
            except ImportError as e:
                logger.warning(f"⚠️  可视化功能需要额外依赖: {e}")
                logger.info("💡 可以运行: pip install matplotlib networkx")
            except Exception as e:
                logger.error(f"⚠️  可视化过程中出现问题: {e}")
        else:
            logger.info("⏭️  跳过所有可视化 (使用了 --no-visualization)")
        
        # 显示完成信息
        logger.info("🎉 增强演示完成!")
        logger.info(f"📁 输出目录: {Config.OUTPUT_DIR}/{session_dir}/")
        
        if session_manager and args.save_session:
            logger.info("💡 会话恢复提示:")
            logger.info(f"   要恢复此会话，请运行:")
            logger.info(f"   python enhanced_demo.py --resume {session_dir}")
        
        logger.info("📊 可以使用以下命令查看输出文件:")
        logger.info(f"   ls {Config.OUTPUT_DIR}/{session_dir}/")
        
        return True
        
    except KeyboardInterrupt:
        logger.warning("⚠️  用户中断操作")
        # 如果启用了会话保存，尝试保存当前状态
        if 'session_manager' in locals() and 'crawler' in locals() and args.save_session:
            try:
                session_manager.force_save(crawler)
                logger.info("💾 中断前已保存会话状态")
            except:
                pass
        return False
    except Exception as e:
        logger.error(f"❌ 增强演示过程中出现错误: {e}")
        if args.verbose:
            import traceback
            logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = run_enhanced_demo()
    sys.exit(0 if success else 1)

'''
python /Users/shufanzhang/Documents/coderepos/papertracer/enhanced_demo.py --url "https://scholar.google.com/scholar?cites=10749086880817846297&as_sdt=2005&sciodt=0,5&hl=en" --config demo --depth 5 --max-papers 10 --manual-captcha --no-delays

# 使用429跳过模式的示例（极速模式，跳过所有429错误）:
python /Users/shufanzhang/Documents/coderepos/papertracer/enhanced_demo.py --url "https://scholar.google.com/scholar?cites=10749086880817846297&as_sdt=2005&sciodt=0,5&hl=en" --config demo --depth 3 --max-papers 5 --skip-429 --no-delays
'''