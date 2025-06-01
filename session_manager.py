#!/usr/bin/env python3
"""
PaperTracer 会话管理工具
用于分析、恢复和管理爬虫会话
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from papertracer_config import Config
from logger import get_logger

def setup_session_manager_parser():
    """设置会话管理器命令行参数"""
    parser = argparse.ArgumentParser(
        description='PaperTracer 会话管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
功能:
  list              - 列出所有可用会话
  analyze SESSION   - 分析指定会话的统计信息
  cleanup           - 清理过期或无效会话
  merge SESSION1 SESSION2 - 合并两个会话的数据
  export SESSION    - 导出会话数据为可读格式

示例用法:
  python session_manager.py list
  python session_manager.py analyze demo_20240602_123456
  python session_manager.py cleanup --days 30
  python session_manager.py export demo_20240602_123456 --format csv
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有会话')
    list_parser.add_argument('--recent', type=int, help='只显示最近N个会话')
    list_parser.add_argument('--detailed', action='store_true', help='显示详细信息')
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析会话')
    analyze_parser.add_argument('session_id', help='会话ID')
    analyze_parser.add_argument('--export-stats', help='导出统计信息到文件')
    
    # cleanup 命令
    cleanup_parser = subparsers.add_parser('cleanup', help='清理会话')
    cleanup_parser.add_argument('--days', type=int, default=30, help='删除N天前的会话')
    cleanup_parser.add_argument('--dry-run', action='store_true', help='只显示将被删除的会话，不实际删除')
    cleanup_parser.add_argument('--force', action='store_true', help='强制删除，不询问确认')
    
    # merge 命令
    merge_parser = subparsers.add_parser('merge', help='合并会话')
    merge_parser.add_argument('session1', help='第一个会话ID')
    merge_parser.add_argument('session2', help='第二个会话ID')
    merge_parser.add_argument('--output', help='输出会话名称')
    
    # export 命令
    export_parser = subparsers.add_parser('export', help='导出会话数据')
    export_parser.add_argument('session_id', help='会话ID')
    export_parser.add_argument('--format', choices=['json', 'csv', 'txt'], default='txt', help='导出格式')
    export_parser.add_argument('--output', help='输出文件路径')
    
    return parser

class SessionManager:
    """会话管理器类"""
    
    def __init__(self):
        self.logger = get_logger()
        self.output_dir = Path(Config.OUTPUT_DIR)
        
    def get_all_sessions(self):
        """获取所有会话目录"""
        sessions = []
        if not self.output_dir.exists():
            return sessions
            
        for item in self.output_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                session_info = self._get_session_info(item)
                if session_info:
                    sessions.append(session_info)
        
        return sorted(sessions, key=lambda x: x['created_time'], reverse=True)
    
    def _get_session_info(self, session_dir):
        """获取会话基本信息"""
        try:
            session_state_file = session_dir / "session_state.json"
            citation_files = list(session_dir.glob("*citation_tree*.json"))
            
            info = {
                'id': session_dir.name,
                'path': session_dir,
                'created_time': datetime.fromtimestamp(session_dir.stat().st_ctime),
                'modified_time': datetime.fromtimestamp(session_dir.stat().st_mtime),
                'has_session_state': session_state_file.exists(),
                'has_citation_data': len(citation_files) > 0,
                'file_count': len(list(session_dir.iterdir())),
                'size_mb': sum(f.stat().st_size for f in session_dir.rglob('*') if f.is_file()) / (1024 * 1024)
            }
            
            # 如果有会话状态文件，读取详细信息
            if info['has_session_state']:
                try:
                    with open(session_state_file, 'r') as f:
                        state = json.load(f)
                    info.update({
                        'request_count': state.get('request_count', 0),
                        'visited_urls': len(state.get('visited_urls', [])),
                        'consecutive_429_count': state.get('consecutive_429_count', 0),
                        'last_429_time': state.get('last_429_time')
                    })
                except:
                    pass
            
            return info
        except:
            return None
    
    def list_sessions(self, recent=None, detailed=False):
        """列出会话"""
        sessions = self.get_all_sessions()
        
        if recent:
            sessions = sessions[:recent]
        
        if not sessions:
            self.logger.info("没有找到任何会话")
            return
        
        self.logger.info(f"找到 {len(sessions)} 个会话:")
        self.logger.info("=" * 80)
        
        for session in sessions:
            age = datetime.now() - session['created_time']
            age_str = f"{age.days}天前" if age.days > 0 else "今天"
            
            status = "🟢" if session['has_citation_data'] else "🟡"
            if session['has_session_state']:
                status += " 📊"
            
            self.logger.info(f"{status} {session['id']}")
            self.logger.info(f"    创建时间: {session['created_time'].strftime('%Y-%m-%d %H:%M:%S')} ({age_str})")
            self.logger.info(f"    大小: {session['size_mb']:.1f} MB, 文件数: {session['file_count']}")
            
            if detailed and session['has_session_state']:
                self.logger.info(f"    请求数: {session.get('request_count', 0)}")
                self.logger.info(f"    访问URL数: {session.get('visited_urls', 0)}")
                self.logger.info(f"    429错误: {session.get('consecutive_429_count', 0)}")
            
            self.logger.info("")
    
    def analyze_session(self, session_id, export_stats=None):
        """分析指定会话"""
        session_dir = self.output_dir / session_id
        if not session_dir.exists():
            self.logger.error(f"会话不存在: {session_id}")
            return False
        
        session_info = self._get_session_info(session_dir)
        if not session_info:
            self.logger.error(f"无法读取会话信息: {session_id}")
            return False
        
        self.logger.info(f"📊 会话分析: {session_id}")
        self.logger.info("=" * 60)
        
        # 基本信息
        self.logger.info("基本信息:")
        self.logger.info(f"  创建时间: {session_info['created_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  修改时间: {session_info['modified_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  文件大小: {session_info['size_mb']:.1f} MB")
        self.logger.info(f"  文件数量: {session_info['file_count']}")
        
        # 爬虫统计
        if session_info['has_session_state']:
            self.logger.info("\n爬虫统计:")
            self.logger.info(f"  总请求数: {session_info.get('request_count', 0)}")
            self.logger.info(f"  访问URL数: {session_info.get('visited_urls', 0)}")
            self.logger.info(f"  429错误次数: {session_info.get('consecutive_429_count', 0)}")
            
            if session_info.get('last_429_time'):
                self.logger.info(f"  最后429错误: {session_info['last_429_time']}")
        
        # 文件分析
        files = list(session_dir.iterdir())
        file_types = {}
        for file in files:
            if file.is_file():
                ext = file.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1
        
        self.logger.info("\n文件类型分布:")
        for ext, count in sorted(file_types.items()):
            self.logger.info(f"  {ext or '无扩展名'}: {count} 个文件")
        
        # 引用数据分析
        citation_files = list(session_dir.glob("*citation_tree*.json"))
        if citation_files:
            self.logger.info("\n引用树分析:")
            for citation_file in citation_files:
                try:
                    with open(citation_file, 'r') as f:
                        tree_data = json.load(f)
                    
                    # 统计节点数量
                    node_count = self._count_nodes(tree_data)
                    max_depth = self._get_max_depth(tree_data, 0)
                    
                    self.logger.info(f"  文件: {citation_file.name}")
                    self.logger.info(f"    节点总数: {node_count}")
                    self.logger.info(f"    最大深度: {max_depth}")
                    
                except Exception as e:
                    self.logger.warning(f"  无法分析 {citation_file.name}: {e}")
        
        # 导出统计信息
        if export_stats:
            stats = {
                'session_id': session_id,
                'analysis_time': datetime.now().isoformat(),
                'basic_info': {
                    'created_time': session_info['created_time'].isoformat(),
                    'size_mb': session_info['size_mb'],
                    'file_count': session_info['file_count']
                },
                'crawler_stats': {
                    'request_count': session_info.get('request_count', 0),
                    'visited_urls': session_info.get('visited_urls', 0),
                    'consecutive_429_count': session_info.get('consecutive_429_count', 0)
                },
                'file_types': file_types
            }
            
            try:
                with open(export_stats, 'w') as f:
                    json.dump(stats, f, indent=2)
                self.logger.info(f"\n✅ 统计信息已导出到: {export_stats}")
            except Exception as e:
                self.logger.error(f"导出统计信息失败: {e}")
        
        return True
    
    def _count_nodes(self, node):
        """递归计算节点数量"""
        if not node:
            return 0
        count = 1
        if 'children' in node:
            for child in node['children']:
                count += self._count_nodes(child)
        return count
    
    def _get_max_depth(self, node, current_depth):
        """递归计算最大深度"""
        if not node or 'children' not in node or not node['children']:
            return current_depth
        
        max_child_depth = current_depth
        for child in node['children']:
            child_depth = self._get_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
        
        return max_child_depth
    
    def cleanup_sessions(self, days=30, dry_run=False, force=False):
        """清理过期会话"""
        cutoff_date = datetime.now() - timedelta(days=days)
        sessions = self.get_all_sessions()
        
        old_sessions = [s for s in sessions if s['created_time'] < cutoff_date]
        
        if not old_sessions:
            self.logger.info(f"没有找到 {days} 天前的会话")
            return
        
        self.logger.info(f"找到 {len(old_sessions)} 个超过 {days} 天的会话:")
        
        total_size = sum(s['size_mb'] for s in old_sessions)
        for session in old_sessions:
            age = datetime.now() - session['created_time']
            self.logger.info(f"  - {session['id']} ({session['size_mb']:.1f} MB, {age.days} 天前)")
        
        self.logger.info(f"总大小: {total_size:.1f} MB")
        
        if dry_run:
            self.logger.info("\n🔍 这是预览模式，没有实际删除任何文件")
            return
        
        if not force:
            response = input(f"\n确定要删除这 {len(old_sessions)} 个会话吗? (y/N): ")
            if response.lower() != 'y':
                self.logger.info("操作已取消")
                return
        
        # 执行删除
        deleted_count = 0
        for session in old_sessions:
            try:
                import shutil
                shutil.rmtree(session['path'])
                deleted_count += 1
                self.logger.info(f"✅ 已删除: {session['id']}")
            except Exception as e:
                self.logger.error(f"❌ 删除失败 {session['id']}: {e}")
        
        self.logger.info(f"\n🧹 清理完成: 删除了 {deleted_count}/{len(old_sessions)} 个会话")
    
    def merge_sessions(self, session1_id, session2_id, output_name=None):
        """合并两个会话的数据"""
        self.logger.info(f"🔄 合并会话: {session1_id} + {session2_id}")
        
        # 获取会话信息
        session1_info = self._find_session(session1_id)
        session2_info = self._find_session(session2_id)
        
        if not session1_info or not session2_info:
            raise ValueError("未找到指定的会话")
        
        # 创建输出目录
        if not output_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"merged_{timestamp}"
        
        output_dir = self.output_dir / output_name
        output_dir.mkdir(exist_ok=True)
        
        # 合并引用树数据
        merged_tree = self._merge_citation_trees(session1_info, session2_info)
        
        # 保存合并后的数据
        output_file = output_dir / "merged_citation_tree.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_tree, f, indent=2, ensure_ascii=False)
        
        # 合并会话状态
        merged_state = self._merge_session_states(session1_info, session2_info)
        state_file = output_dir / "session_state.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(merged_state, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"✅ 会话合并完成: {output_dir}")
        return output_dir
    
    def export_session(self, session_id, format_type='txt', output_file=None):
        """导出会话数据为指定格式"""
        self.logger.info(f"📤 导出会话: {session_id} (格式: {format_type})")
        
        session_info = self._find_session(session_id)
        if not session_info:
            raise ValueError(f"未找到会话: {session_id}")
        
        # 加载引用树数据
        citation_files = list(session_info['path'].glob("*citation_tree*.json"))
        if not citation_files:
            raise ValueError(f"会话中未找到引用树数据: {session_id}")
        
        with open(citation_files[0], 'r', encoding='utf-8') as f:
            tree_data = json.load(f)
        
        # 确定输出文件名
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"export_{session_id}_{timestamp}.{format_type}"
        
        # 根据格式导出
        if format_type == 'json':
            self._export_json(tree_data, output_file)
        elif format_type == 'csv':
            self._export_csv(tree_data, output_file)
        elif format_type == 'txt':
            self._export_txt(tree_data, output_file)
        
        self.logger.info(f"✅ 导出完成: {output_file}")
        return output_file
    
    def _find_session(self, session_id):
        """查找指定会话"""
        sessions = self.get_all_sessions()
        for session in sessions:
            if session['id'] == session_id:
                return session
        return None
    
    def _merge_citation_trees(self, session1, session2):
        """合并两个会话的引用树数据"""
        # 加载两个会话的引用树
        tree1_files = list(session1['path'].glob("*citation_tree*.json"))
        tree2_files = list(session2['path'].glob("*citation_tree*.json"))
        
        tree1_data = {}
        tree2_data = {}
        
        if tree1_files:
            with open(tree1_files[0], 'r', encoding='utf-8') as f:
                tree1_data = json.load(f)
        
        if tree2_files:
            with open(tree2_files[0], 'r', encoding='utf-8') as f:
                tree2_data = json.load(f)
        
        # 简单合并策略：以第一个会话为基础，添加第二个会话的数据
        merged = tree1_data.copy()
        
        if 'metadata' in tree2_data:
            merged.setdefault('metadata', {})
            merged['metadata']['merged_from'] = [session1['id'], session2['id']]
            merged['metadata']['merge_time'] = datetime.now().isoformat()
        
        # 合并节点数据（可以根据需要实现更复杂的合并逻辑）
        if 'root' in tree2_data and tree2_data['root']:
            if 'additional_roots' not in merged:
                merged['additional_roots'] = []
            merged['additional_roots'].append(tree2_data['root'])
        
        return merged
    
    def _merge_session_states(self, session1, session2):
        """合并两个会话的状态数据"""
        state1_file = session1['path'] / "session_state.json"
        state2_file = session2['path'] / "session_state.json"
        
        state1 = {}
        state2 = {}
        
        if state1_file.exists():
            with open(state1_file, 'r', encoding='utf-8') as f:
                state1 = json.load(f)
        
        if state2_file.exists():
            with open(state2_file, 'r', encoding='utf-8') as f:
                state2 = json.load(f)
        
        # 合并会话状态
        merged_state = {
            'merged_from': [session1['id'], session2['id']],
            'merge_time': datetime.now().isoformat(),
            'session1_state': state1,
            'session2_state': state2,
            'request_count': state1.get('request_count', 0) + state2.get('request_count', 0),
            'visited_urls': list(set(
                state1.get('visited_urls', []) + state2.get('visited_urls', [])
            ))
        }
        
        return merged_state
    
    def _export_json(self, data, output_file):
        """导出为JSON格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_csv(self, data, output_file):
        """导出为CSV格式"""
        import csv
        
        # 提取论文数据为平面结构
        papers = []
        self._extract_papers_for_csv(data.get('root', {}), papers, depth=0)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if papers:
                writer = csv.DictWriter(f, fieldnames=papers[0].keys())
                writer.writeheader()
                writer.writerows(papers)
    
    def _export_txt(self, data, output_file):
        """导出为文本格式"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PaperTracer 引用树导出\n")
            f.write("=" * 50 + "\n\n")
            
            if 'metadata' in data:
                f.write("元数据:\n")
                for key, value in data['metadata'].items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
            
            if 'root' in data:
                f.write("引用树结构:\n")
                self._write_tree_structure(data['root'], f, depth=0)
    
    def _extract_papers_for_csv(self, node, papers, depth=0):
        """递归提取论文数据为CSV格式"""
        if 'paper' in node:
            paper = node['paper'].copy()
            paper['depth'] = depth
            paper['children_count'] = len(node.get('children', []))
            papers.append(paper)
        
        for child in node.get('children', []):
            self._extract_papers_for_csv(child, papers, depth + 1)
    
    def _write_tree_structure(self, node, file, depth=0):
        """递归写入树结构到文本文件"""
        indent = "  " * depth
        if 'paper' in node:
            paper = node['paper']
            file.write(f"{indent}- {paper.get('title', 'Unknown Title')}\n")
            file.write(f"{indent}  作者: {paper.get('authors', 'Unknown')}\n")
            file.write(f"{indent}  年份: {paper.get('year', 'Unknown')}\n")
            file.write(f"{indent}  引用次数: {paper.get('citation_count', 0)}\n")
            if paper.get('url'):
                file.write(f"{indent}  链接: {paper['url']}\n")
            file.write("\n")
        
        for child in node.get('children', []):
            self._write_tree_structure(child, file, depth + 1)

def main():
    """主函数"""
    parser = setup_session_manager_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    session_manager = SessionManager()
    
    try:
        if args.command == 'list':
            session_manager.list_sessions(args.recent, args.detailed)
            
        elif args.command == 'analyze':
            session_manager.analyze_session(args.session_id, args.export_stats)
            
        elif args.command == 'cleanup':
            session_manager.cleanup_sessions(args.days, args.dry_run, args.force)
            
        elif args.command == 'merge':
            session_manager.merge_sessions(args.session1, args.session2, args.output)
            
        elif args.command == 'export':
            session_manager.export_session(args.session_id, args.format, args.output)
            
    except KeyboardInterrupt:
        print("\n操作被用户中断")
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    main()
