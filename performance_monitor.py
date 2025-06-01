#!/usr/bin/env python3
"""
PaperTracer 性能监控工具
实时监控爬虫性能，检测异常情况并提供优化建议
"""

import sys
import os
import json
import time
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Optional
from papertracer_config import Config
from logger import get_logger

@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    timestamp: datetime
    requests_per_minute: float
    average_delay: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    network_latency_ms: float
    consecutive_429_count: int
    success_rate: float

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, session_dir: str = None):
        self.logger = get_logger()
        self.session_dir = Path(session_dir) if session_dir else None
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_time = datetime.now()
        self.last_request_count = 0
        self.last_check_time = datetime.now()
        
    def collect_system_metrics(self) -> Dict:
        """收集系统性能指标"""
        process = psutil.Process()
        
        return {
            'memory_usage_mb': process.memory_info().rss / (1024 * 1024),
            'cpu_usage_percent': process.cpu_percent(),
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent(),
            'network_connections': len(process.connections()),
            'open_files': len(process.open_files())
        }
    
    def collect_crawler_metrics(self, crawler) -> Dict:
        """收集爬虫性能指标"""
        current_time = datetime.now()
        time_diff = (current_time - self.last_check_time).total_seconds()
        
        # 计算请求速率
        request_diff = crawler.request_count - self.last_request_count
        requests_per_minute = (request_diff / time_diff) * 60 if time_diff > 0 else 0
        
        # 更新记录
        self.last_request_count = crawler.request_count
        self.last_check_time = current_time
        
        # 计算成功率
        total_attempts = crawler.request_count
        success_rate = 1.0 - (crawler.consecutive_429_count / max(total_attempts, 1))
        
        return {
            'total_requests': crawler.request_count,
            'requests_per_minute': requests_per_minute,
            'visited_urls': len(crawler.visited_urls),
            'consecutive_429_count': getattr(crawler, 'consecutive_429_count', 0),
            'success_rate': success_rate,
            'last_429_time': getattr(crawler, 'last_429_time', None),
            'session_duration_minutes': (current_time - self.start_time).total_seconds() / 60
        }
    
    def measure_network_latency(self) -> float:
        """测量网络延迟"""
        import requests
        try:
            start_time = time.time()
            response = requests.head('https://scholar.google.com', timeout=5)
            latency = (time.time() - start_time) * 1000
            return latency
        except:
            return -1  # 表示测量失败
    
    def create_performance_snapshot(self, crawler) -> PerformanceMetrics:
        """创建性能快照"""
        system_metrics = self.collect_system_metrics()
        crawler_metrics = self.collect_crawler_metrics(crawler)
        network_latency = self.measure_network_latency()
        
        # 估算平均延迟
        delay_range = getattr(crawler, 'delay_range', (2, 5))
        estimated_delay = sum(delay_range) / 2
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            requests_per_minute=crawler_metrics['requests_per_minute'],
            average_delay=estimated_delay,
            error_rate=1.0 - crawler_metrics['success_rate'],
            memory_usage_mb=system_metrics['memory_usage_mb'],
            cpu_usage_percent=system_metrics['cpu_usage_percent'],
            network_latency_ms=network_latency,
            consecutive_429_count=crawler_metrics['consecutive_429_count'],
            success_rate=crawler_metrics['success_rate']
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def analyze_performance_trends(self) -> Dict:
        """分析性能趋势"""
        if len(self.metrics_history) < 2:
            return {'status': 'insufficient_data'}
        
        recent_metrics = self.metrics_history[-5:]  # 最近5个数据点
        old_metrics = self.metrics_history[-10:-5] if len(self.metrics_history) >= 10 else self.metrics_history[:-5]
        
        if not old_metrics:
            return {'status': 'insufficient_historical_data'}
        
        # 计算趋势
        recent_avg_rpm = sum(m.requests_per_minute for m in recent_metrics) / len(recent_metrics)
        old_avg_rpm = sum(m.requests_per_minute for m in old_metrics) / len(old_metrics)
        
        recent_avg_error = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        old_avg_error = sum(m.error_rate for m in old_metrics) / len(old_metrics)
        
        recent_avg_latency = sum(m.network_latency_ms for m in recent_metrics if m.network_latency_ms > 0)
        recent_avg_latency = recent_avg_latency / len([m for m in recent_metrics if m.network_latency_ms > 0]) if recent_avg_latency else 0
        
        return {
            'status': 'analyzed',
            'rpm_trend': 'improving' if recent_avg_rpm > old_avg_rpm else 'declining',
            'rpm_change_percent': ((recent_avg_rpm - old_avg_rpm) / max(old_avg_rpm, 1)) * 100,
            'error_trend': 'improving' if recent_avg_error < old_avg_error else 'worsening',
            'error_change_percent': ((recent_avg_error - old_avg_error) / max(old_avg_error, 0.01)) * 100,
            'average_latency_ms': recent_avg_latency,
            'current_rpm': recent_avg_rpm,
            'current_error_rate': recent_avg_error
        }
    
    def generate_optimization_recommendations(self, trends: Dict, current_metrics: PerformanceMetrics) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 内存使用建议
        if current_metrics.memory_usage_mb > 500:
            recommendations.append("⚠️  内存使用过高 (>500MB)，考虑降低max_papers_per_level或重启爬虫")
        
        # CPU使用建议
        if current_metrics.cpu_usage_percent > 80:
            recommendations.append("⚠️  CPU使用率过高，考虑增加延迟时间")
        
        # 网络延迟建议
        if current_metrics.network_latency_ms > 2000:
            recommendations.append("⚠️  网络延迟过高 (>2s)，可能需要检查网络连接或使用代理")
        elif current_metrics.network_latency_ms < 0:
            recommendations.append("❌ 无法连接到Google Scholar，请检查网络连接")
        
        # 429错误建议
        if current_metrics.consecutive_429_count > 3:
            recommendations.append("🚨 连续429错误过多，建议：1) 增加延迟 2) 更换User-Agent 3) 使用代理")
        elif current_metrics.consecutive_429_count > 0:
            recommendations.append("⚠️  遇到429错误，系统正在自动调整延迟策略")
        
        # 成功率建议
        if current_metrics.success_rate < 0.8:
            recommendations.append("⚠️  成功率偏低 (<80%)，建议检查网络和延迟配置")
        elif current_metrics.success_rate > 0.95:
            recommendations.append("✅ 成功率良好 (>95%)，可以考虑适当降低延迟以提高效率")
        
        # 请求速率建议
        if trends.get('status') == 'analyzed':
            current_rpm = trends['current_rpm']
            if current_rpm < 1:
                recommendations.append("⚠️  请求速率过低 (<1/min)，考虑降低延迟或检查是否被阻止")
            elif current_rpm > 10:
                recommendations.append("⚠️  请求速率可能过高 (>10/min)，建议增加延迟以避免被检测")
        
        # 趋势建议
        if trends.get('rpm_trend') == 'declining' and trends.get('rpm_change_percent', 0) < -20:
            recommendations.append("📉 请求速率下降明显，可能遇到了反爬虫限制")
        
        if trends.get('error_trend') == 'worsening':
            recommendations.append("📈 错误率上升，建议暂停并调整策略")
        
        if not recommendations:
            recommendations.append("✅ 当前性能良好，继续保持")
        
        return recommendations
    
    def save_performance_report(self, filepath: str):
        """保存性能报告"""
        if not self.metrics_history:
            self.logger.warning("没有性能数据可保存")
            return
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'session_duration_minutes': (datetime.now() - self.start_time).total_seconds() / 60,
            'total_metrics_collected': len(self.metrics_history),
            'summary': {
                'avg_requests_per_minute': sum(m.requests_per_minute for m in self.metrics_history) / len(self.metrics_history),
                'avg_success_rate': sum(m.success_rate for m in self.metrics_history) / len(self.metrics_history),
                'max_memory_usage_mb': max(m.memory_usage_mb for m in self.metrics_history),
                'avg_network_latency_ms': sum(m.network_latency_ms for m in self.metrics_history if m.network_latency_ms > 0) / max(len([m for m in self.metrics_history if m.network_latency_ms > 0]), 1),
                'max_consecutive_429_count': max(m.consecutive_429_count for m in self.metrics_history)
            },
            'metrics_history': [
                {
                    'timestamp': m.timestamp.isoformat(),
                    'requests_per_minute': m.requests_per_minute,
                    'success_rate': m.success_rate,
                    'memory_usage_mb': m.memory_usage_mb,
                    'cpu_usage_percent': m.cpu_usage_percent,
                    'network_latency_ms': m.network_latency_ms,
                    'consecutive_429_count': m.consecutive_429_count
                }
                for m in self.metrics_history
            ]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            self.logger.info(f"性能报告已保存到: {filepath}")
        except Exception as e:
            self.logger.error(f"保存性能报告失败: {e}")
    
    def print_live_dashboard(self, current_metrics: PerformanceMetrics, trends: Dict, recommendations: List[str]):
        """打印实时监控面板"""
        print("\n" + "="*80)
        print("🔍 PaperTracer 实时性能监控")
        print("="*80)
        print(f"⏰ 时间: {current_metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⚡ 会话时长: {(datetime.now() - self.start_time).total_seconds() / 60:.1f} 分钟")
        print()
        
        # 核心指标
        print("📊 核心指标:")
        print(f"   请求速率: {current_metrics.requests_per_minute:.1f} 请求/分钟")
        print(f"   成功率: {current_metrics.success_rate:.1%}")
        print(f"   网络延迟: {current_metrics.network_latency_ms:.0f} ms" if current_metrics.network_latency_ms > 0 else "   网络延迟: 测量失败")
        print(f"   429错误: {current_metrics.consecutive_429_count} 次连续")
        print()
        
        # 系统资源
        print("💻 系统资源:")
        print(f"   内存使用: {current_metrics.memory_usage_mb:.1f} MB")
        print(f"   CPU使用: {current_metrics.cpu_usage_percent:.1f}%")
        print()
        
        # 趋势分析
        if trends.get('status') == 'analyzed':
            print("📈 趋势分析:")
            rpm_trend_icon = "📈" if trends['rpm_trend'] == 'improving' else "📉"
            error_trend_icon = "📉" if trends['error_trend'] == 'improving' else "📈"
            print(f"   请求速率: {rpm_trend_icon} {trends['rpm_trend']} ({trends['rpm_change_percent']:+.1f}%)")
            print(f"   错误率: {error_trend_icon} {trends['error_trend']} ({trends['error_change_percent']:+.1f}%)")
            print()
        
        # 优化建议
        print("💡 优化建议:")
        for i, recommendation in enumerate(recommendations[:5], 1):
            print(f"   {i}. {recommendation}")
        
        print("="*80)

def run_performance_monitor():
    """运行性能监控器"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PaperTracer 性能监控')
    parser.add_argument('--session-dir', help='要监控的会话目录')
    parser.add_argument('--interval', type=int, default=30, help='监控间隔（秒）')
    parser.add_argument('--output', help='性能报告输出文件')
    parser.add_argument('--quiet', action='store_true', help='静默模式，只输出警告')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.session_dir)
    logger = get_logger()
    
    logger.info("🔍 启动性能监控器...")
    logger.info(f"监控间隔: {args.interval} 秒")
    
    if args.session_dir:
        session_state_file = Path(args.session_dir) / "session_state.json"
        if not session_state_file.exists():
            logger.warning(f"会话状态文件不存在: {session_state_file}")
    
    try:
        while True:
            # 这里应该连接到实际的爬虫实例
            # 为了演示，我们创建一个模拟的爬虫对象
            class MockCrawler:
                def __init__(self):
                    self.request_count = 50
                    self.visited_urls = set(range(25))
                    self.consecutive_429_count = 2
                    self.delay_range = (3, 6)
            
            mock_crawler = MockCrawler()
            
            # 收集性能指标
            current_metrics = monitor.create_performance_snapshot(mock_crawler)
            trends = monitor.analyze_performance_trends()
            recommendations = monitor.generate_optimization_recommendations(trends, current_metrics)
            
            # 显示监控面板
            if not args.quiet:
                monitor.print_live_dashboard(current_metrics, trends, recommendations)
            else:
                # 静默模式下只显示警告
                warnings = [r for r in recommendations if any(icon in r for icon in ['⚠️', '🚨', '❌'])]
                for warning in warnings:
                    logger.warning(warning)
            
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("\n监控已停止")
        
        # 保存性能报告
        if args.output:
            monitor.save_performance_report(args.output)
        elif args.session_dir:
            default_report = Path(args.session_dir) / f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            monitor.save_performance_report(str(default_report))

if __name__ == "__main__":
    run_performance_monitor()
