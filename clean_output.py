#!/usr/bin/env python3
"""
输出文件清理工具
用于管理 output/ 目录中的生成文件
"""

import os
import glob
import argparse
from datetime import datetime, timedelta
from papertracer_config import Config

def parse_timestamp_from_dirname(dirname):
    """从目录名中解析时间戳"""
    try:
        # 提取时间戳部分，格式：demo_YYYYMMDD_HHMMSS
        parts = dirname.split('_')
        if len(parts) >= 3:
            date_str = parts[1]  # YYYYMMDD
            time_str = parts[2]  # HHMMSS
            
            # 解析日期和时间
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            return datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        pass
    return None

def parse_timestamp_from_filename(filename):
    """从文件名中解析时间戳"""
    try:
        # 提取时间戳部分，格式：demo_YYYYMMDD_HHMMSS_xxx.ext
        parts = filename.split('_')
        if len(parts) >= 3:
            date_str = parts[1]  # YYYYMMDD
            time_str = parts[2]  # HHMMSS
            
            # 解析日期和时间
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])
            
            return datetime(year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        pass
    return None

def get_directory_size(directory):
    """计算目录总大小"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size

def list_output_sessions(output_dir=None):
    """列出输出目录中的所有会话目录"""
    if output_dir is None:
        output_dir = Config.OUTPUT_DIR
        
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录 {output_dir} 不存在")
        return []
    
    # 收集会话目录
    session_dirs = []
    for item in os.listdir(output_dir):
        item_path = os.path.join(output_dir, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            timestamp = parse_timestamp_from_dirname(item)
            dir_size = get_directory_size(item_path)
            
            # 统计目录中的文件
            file_count = 0
            for root, dirs, files in os.walk(item_path):
                file_count += len(files)
            
            session_dirs.append((item_path, item, timestamp, dir_size, file_count))
    
    # 按时间戳排序（最新的在前）
    session_dirs.sort(key=lambda x: x[2] or datetime.min, reverse=True)
    return session_dirs

def list_output_files(output_dir=None):
    """列出输出目录中的所有文件（包括老格式的散落文件）"""
    if output_dir is None:
        output_dir = Config.OUTPUT_DIR
        
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录 {output_dir} 不存在")
        return []
    
    # 收集直接在输出目录下的文件（老格式）
    files = []
    for pattern in Config.get_all_output_patterns():
        files.extend(glob.glob(os.path.join(output_dir, pattern)))
    
    # 过滤掉目录
    files = [f for f in files if os.path.isfile(f)]
    
    # 按时间戳排序
    file_info = []
    for file_path in files:
        filename = os.path.basename(file_path)
        timestamp = parse_timestamp_from_filename(filename)
        file_size = os.path.getsize(file_path)
        file_info.append((file_path, filename, timestamp, file_size))
    
    # 按时间戳排序（最新的在前）
    file_info.sort(key=lambda x: x[2] or datetime.min, reverse=True)
    return file_info

def clean_old_sessions(output_dir="output", days=7, dry_run=True):
    """清理指定天数之前的会话目录"""
    cutoff_date = datetime.now() - timedelta(days=days)
    session_dirs = list_output_sessions(output_dir)
    
    old_sessions = []
    for dir_path, dirname, timestamp, dir_size, file_count in session_dirs:
        if timestamp and timestamp < cutoff_date:
            old_sessions.append((dir_path, dirname, timestamp, dir_size, file_count))
    
    if not old_sessions:
        print(f"✅ 没有找到 {days} 天前的会话目录")
        return
    
    print(f"🗑️  找到 {len(old_sessions)} 个 {days} 天前的会话目录:")
    total_size = 0
    for dir_path, dirname, timestamp, dir_size, file_count in old_sessions:
        size_mb = dir_size / (1024 * 1024)
        total_size += dir_size
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知"
        print(f"   - {dirname}/ ({file_count} 个文件, {size_mb:.2f} MB, {timestamp_str})")
    
    print(f"📊 总大小: {total_size / (1024 * 1024):.2f} MB")
    
    if dry_run:
        print("\n💡 这是预览模式，使用 --confirm 参数实际删除目录")
    else:
        confirm = input("\n❓ 确认删除这些会话目录吗? (y/N): ")
        if confirm.lower() == 'y':
            import shutil
            for dir_path, dirname, timestamp, dir_size, file_count in old_sessions:
                try:
                    shutil.rmtree(dir_path)
                    print(f"✅ 已删除: {dirname}/")
                except Exception as e:
                    print(f"❌ 删除失败 {dirname}/: {e}")
        else:
            print("❌ 取消删除操作")

def clean_old_files(output_dir="output", days=7, dry_run=True):
    """清理指定天数之前的文件（老格式的散落文件）"""
    cutoff_date = datetime.now() - timedelta(days=days)
    file_info = list_output_files(output_dir)
    
    old_files = []
    for file_path, filename, timestamp, file_size in file_info:
        if timestamp and timestamp < cutoff_date:
            old_files.append((file_path, filename, timestamp, file_size))
    
    if not old_files:
        print(f"✅ 没有找到 {days} 天前的散落文件")
        return
    
    print(f"🗑️  找到 {len(old_files)} 个 {days} 天前的散落文件:")
    total_size = 0
    for file_path, filename, timestamp, file_size in old_files:
        size_mb = file_size / (1024 * 1024)
        total_size += file_size
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知"
        print(f"   - {filename} ({size_mb:.2f} MB, {timestamp_str})")
    
    print(f"📊 总大小: {total_size / (1024 * 1024):.2f} MB")
    
    if dry_run:
        print("\n💡 这是预览模式，使用 --confirm 参数实际删除文件")
    else:
        confirm = input("\n❓ 确认删除这些文件吗? (y/N): ")
        if confirm.lower() == 'y':
            for file_path, filename, timestamp, file_size in old_files:
                try:
                    os.remove(file_path)
                    print(f"✅ 已删除: {filename}")
                except Exception as e:
                    print(f"❌ 删除失败 {filename}: {e}")
        else:
            print("❌ 取消删除操作")

def main():
    parser = argparse.ArgumentParser(description="PaperTracer 输出文件管理工具")
    parser.add_argument("--output-dir", default="output", help="输出目录路径")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 列出会话命令
    list_parser = subparsers.add_parser("list", help="列出所有爬取会话")
    
    # 列出散落文件命令
    files_parser = subparsers.add_parser("files", help="列出散落的文件（老格式）")
    
    # 清理会话命令
    clean_parser = subparsers.add_parser("clean", help="清理旧的会话目录")
    clean_parser.add_argument("--days", type=int, default=7, help="删除几天前的会话 (默认: 7)")
    clean_parser.add_argument("--confirm", action="store_true", help="确认删除（默认为预览模式）")
    
    # 清理散落文件命令
    clean_files_parser = subparsers.add_parser("clean-files", help="清理散落的文件（老格式）")
    clean_files_parser.add_argument("--days", type=int, default=7, help="删除几天前的文件 (默认: 7)")
    clean_files_parser.add_argument("--confirm", action="store_true", help="确认删除（默认为预览模式）")
    
    args = parser.parse_args()
    
    if args.command == "list":
        session_dirs = list_output_sessions(args.output_dir)
        if not session_dirs:
            print("📁 没有找到任何爬取会话")
        else:
            print(f"📁 输出目录: {args.output_dir}")
            print(f"📊 共找到 {len(session_dirs)} 个爬取会话:\n")
            
            for dir_path, dirname, timestamp, dir_size, file_count in session_dirs:
                size_mb = dir_size / (1024 * 1024)
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知时间"
                print(f"📂 {dirname}/")
                print(f"   ⏰ {timestamp_str}")
                print(f"   📄 {file_count} 个文件")
                print(f"   💾 {size_mb:.2f} MB")
                print()
            
            total_size = sum(info[3] for info in session_dirs)
            print(f"💾 总大小: {total_size / (1024 * 1024):.2f} MB")
        
        # 也检查散落的文件
        file_info = list_output_files(args.output_dir)
        if file_info:
            print(f"\n📄 另外发现 {len(file_info)} 个散落文件（老格式）:")
            for file_path, filename, timestamp, file_size in file_info:
                size_mb = file_size / (1024 * 1024)
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知时间"
                print(f"   - {filename} ({size_mb:.2f} MB, {timestamp_str})")
    
    elif args.command == "files":
        file_info = list_output_files(args.output_dir)
        if not file_info:
            print("📁 没有找到散落的文件")
            return
        
        print(f"📁 输出目录: {args.output_dir}")
        print(f"📊 共找到 {len(file_info)} 个散落文件:\n")
        
        for file_path, filename, timestamp, file_size in file_info:
            size_mb = file_size / (1024 * 1024)
            timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "未知时间"
            print(f"📄 {filename}")
            print(f"   ⏰ {timestamp_str}")
            print(f"   💾 {size_mb:.2f} MB")
            print()
        
        total_size = sum(info[3] for info in file_info)
        print(f"💾 总大小: {total_size / (1024 * 1024):.2f} MB")
    
    elif args.command == "clean":
        clean_old_sessions(args.output_dir, args.days, not args.confirm)
    
    elif args.command == "clean-files":
        clean_old_files(args.output_dir, args.days, not args.confirm)
    
    else:
        print("🗂️ PaperTracer 输出文件管理工具\n")
        print("📁 可用命令:")
        print("   list        - 列出所有爬取会话目录")
        print("   files       - 列出散落的文件（老格式）")
        print("   clean       - 清理旧的会话目录")
        print("   clean-files - 清理散落的文件（老格式）")
        print("\n💡 使用示例:")
        print("   python clean_output.py list")
        print("   python clean_output.py files")
        print("   python clean_output.py clean --days 7")
        print("   python clean_output.py clean --days 7 --confirm")
        print("   python clean_output.py clean-files --days 7")
        print("\n📖 详细帮助:")
        print("   python clean_output.py --help")

if __name__ == "__main__":
    main()
