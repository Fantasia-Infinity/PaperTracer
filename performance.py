#!/usr/bin/env python3
"""
PaperTracer 性能监控工具
监控爬虫性能和资源使用情况
"""

import time
import psutil
import os
from datetime import datetime, timedelta
from papertracer_config import Config
from logger import get_logger

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.peak_memory = None
        self.current_memory = None
        self.process = psutil.Process(os.getpid())
        self.logger = get_logger()
        
        # 监控数据
        self.requests_count = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.papers_scraped = 0
        
    def start_monitoring(self):
        """开始监控"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.logger.info(f"🔍 性能监控开始 - 初始内存: {self.start_memory:.1f} MB")
        
    def update_memory(self):
        """更新内存使用情况"""
        self.current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        if self.current_memory > self.peak_memory:
            self.peak_memory = self.current_memory
            
    def record_request(self, success=True):
        """记录请求"""
        self.requests_count += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.update_memory()
        
    def record_paper(self):
        """记录爬取的论文"""
        self.papers_scraped += 1
        
    def stop_monitoring(self):
        """停止监控"""
        self.end_time = time.time()
        self.update_memory()
        
    def get_duration(self):
        """获取运行时长"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0
        
    def get_success_rate(self):
        """获取成功率"""
        if self.requests_count == 0:
            return 0
        return (self.successful_requests / self.requests_count) * 100
        
    def get_average_time_per_paper(self):
        """获取每篇论文的平均处理时间"""
        if self.papers_scraped == 0:
            return 0
        return self.get_duration() / self.papers_scraped
        
    def get_memory_usage_stats(self):
        """获取内存使用统计"""
        return {
            'start_memory': self.start_memory,
            'current_memory': self.current_memory,
            'peak_memory': self.peak_memory,
            'memory_increase': self.current_memory - self.start_memory if self.start_memory else 0
        }
        
    def generate_report(self):
        """生成性能报告"""
        duration = self.get_duration()
        success_rate = self.get_success_rate()
        avg_time_per_paper = self.get_average_time_per_paper()
        memory_stats = self.get_memory_usage_stats()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': duration,
            'duration_formatted': str(timedelta(seconds=int(duration))),
            'requests': {
                'total': self.requests_count,
                'successful': self.successful_requests,
                'failed': self.failed_requests,
                'success_rate_percent': success_rate
            },
            'papers_scraped': self.papers_scraped,
            'average_time_per_paper_seconds': avg_time_per_paper,
            'memory_usage_mb': memory_stats,
            'performance_metrics': {
                'requests_per_second': self.requests_count / duration if duration > 0 else 0,
                'papers_per_minute': (self.papers_scraped / duration) * 60 if duration > 0 else 0,
                'memory_efficiency_mb_per_paper': memory_stats['memory_increase'] / self.papers_scraped if self.papers_scraped > 0 else 0
            }
        }
        
        return report
        
    def print_summary(self):
        """打印性能摘要"""
        duration = self.get_duration()
        success_rate = self.get_success_rate()
        
        self.logger.info("📊 性能监控摘要")
        self.logger.info("-" * 40)
        self.logger.info(f"⏱️  总用时: {timedelta(seconds=int(duration))}")
        self.logger.info(f"📄 爬取论文: {self.papers_scraped} 篇")
        self.logger.info(f"🌐 网络请求: {self.requests_count} 次")
        self.logger.info(f"✅ 成功率: {success_rate:.1f}%")
        
        if self.papers_scraped > 0:
            avg_time = self.get_average_time_per_paper()
            self.logger.info(f"⚡ 平均处理时间: {avg_time:.1f} 秒/篇")
            
        memory_stats = self.get_memory_usage_stats()
        self.logger.info(f"💾 内存使用:")
        self.logger.info(f"   - 起始: {memory_stats['start_memory']:.1f} MB")
        self.logger.info(f"   - 当前: {memory_stats['current_memory']:.1f} MB")
        self.logger.info(f"   - 峰值: {memory_stats['peak_memory']:.1f} MB")
        
    def save_report(self, filename=None):
        """保存性能报告"""
        if filename is None:
            filename = Config.get_timestamped_filename(
                prefix="performance",
                suffix="report",
                extension="json"
            )
            
        report = self.generate_report()
        
        # 确保输出目录存在
        Config.ensure_output_directory()
        filepath = Config.get_output_path(filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            import json
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"📊 性能报告已保存: {filepath}")
        return filepath

# 全局性能监控实例
_global_monitor = None

def get_monitor():
    """获取全局性能监控实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor

def start_monitoring():
    """开始性能监控"""
    monitor = get_monitor()
    monitor.start_monitoring()
    return monitor

def stop_monitoring():
    """停止性能监控并生成报告"""
    monitor = get_monitor()
    monitor.stop_monitoring()
    monitor.print_summary()
    return monitor.save_report()
