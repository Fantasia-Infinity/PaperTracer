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

def list_output_files(output_dir=None):
    """列出输出目录中的所有文件"""
    if output_dir is None:
        output_dir = Config.OUTPUT_DIR
        
    if not os.path.exists(output_dir):
        print(f"❌ 输出目录 {output_dir} 不存在")
        return []
    
    files = []
    for pattern in Config.get_all_output_patterns():
        files.extend(glob.glob(os.path.join(output_dir, pattern)))
    
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

def clean_old_files(output_dir="output", days=7, dry_run=True):
    """清理指定天数之前的文件"""
    cutoff_date = datetime.now() - timedelta(days=days)
    file_info = list_output_files(output_dir)
    
    old_files = []
    for file_path, filename, timestamp, file_size in file_info:
        if timestamp and timestamp < cutoff_date:
            old_files.append((file_path, filename, timestamp, file_size))
    
    if not old_files:
        print(f"✅ 没有找到 {days} 天前的文件")
        return
    
    print(f"🗑️  找到 {len(old_files)} 个 {days} 天前的文件:")
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
    
    # 列出文件命令
    list_parser = subparsers.add_parser("list", help="列出所有输出文件")
    
    # 清理文件命令
    clean_parser = subparsers.add_parser("clean", help="清理旧文件")
    clean_parser.add_argument("--days", type=int, default=7, help="删除几天前的文件 (默认: 7)")
    clean_parser.add_argument("--confirm", action="store_true", help="确认删除（默认为预览模式）")
    
    args = parser.parse_args()
    
    if args.command == "list":
        file_info = list_output_files(args.output_dir)
        if not file_info:
            print("📁 输出目录为空")
            return
        
        print(f"📁 输出目录: {args.output_dir}")
        print(f"📊 共找到 {len(file_info)} 个文件:\n")
        
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
        clean_old_files(args.output_dir, args.days, not args.confirm)
    
    else:
        print("🗂️ PaperTracer 输出文件管理工具\n")
        print("📁 可用命令:")
        print("   list   - 列出所有输出文件")
        print("   clean  - 清理旧文件")
        print("\n💡 使用示例:")
        print("   python clean_output.py list")
        print("   python clean_output.py clean --days 7")
        print("   python clean_output.py clean --days 7 --confirm")
        print("\n📖 详细帮助:")
        print("   python clean_output.py --help")

if __name__ == "__main__":
    main()
