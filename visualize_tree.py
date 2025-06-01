#!/usr/bin/env python3
"""
Google Scholar 引用树可视化工具
使用matplotlib和networkx创建引用关系的可视化图表
"""

import json
import os
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyBboxPatch
import textwrap
from typing import Dict, List, Tuple
import argparse
from papertracer_config import Config

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class CitationTreeVisualizer:
    """引用树可视化器"""
    
    def __init__(self, json_file: str):
        """初始化可视化器"""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.tree_data = json.load(f)
        
        self.graph = nx.DiGraph()
        self.pos = {}
        self.node_labels = {}
        self.node_colors = []
        self.node_sizes = []
        
    def _add_nodes_to_graph(self, node_data: dict, parent_id: str = None, node_id: str = "root"):
        """递归添加节点到图中"""
        paper = node_data['paper']
        depth = node_data['depth']
        
        # 创建节点标签（截断长标题）
        title = paper['title']
        if len(title) > 50:
            title = title[:47] + "..."
        
        # 添加作者和年份信息
        label_parts = [title]
        if paper['authors']:
            authors = paper['authors']
            if len(authors) > 30:
                authors = authors[:27] + "..."
            label_parts.append(f"👥 {authors}")
        
        if paper['year']:
            label_parts.append(f"📅 {paper['year']}")
            
        if paper['citation_count'] > 0:
            label_parts.append(f"📊 {paper['citation_count']} 引用")
        
        self.node_labels[node_id] = '\n'.join(label_parts)
        
        # 根据深度设置颜色
        depth_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        color = depth_colors[depth % len(depth_colors)]
        
        # 根据引用次数设置节点大小
        base_size = 1000
        size = base_size + min(paper['citation_count'] * 10, 2000)
        
        # 添加节点
        self.graph.add_node(node_id, 
                          title=paper['title'],
                          authors=paper['authors'], 
                          year=paper['year'],
                          citations=paper['citation_count'],
                          depth=depth,
                          color=color,
                          size=size)
        
        # 添加边
        if parent_id:
            self.graph.add_edge(parent_id, node_id)
        
        # 递归处理子节点
        for i, child in enumerate(node_data['children']):
            child_id = f"{node_id}_child_{i}"
            self._add_nodes_to_graph(child, node_id, child_id)
    
    def _calculate_layout(self):
        """计算节点布局"""
        # 使用层次化布局
        try:
            # 尝试使用graphviz布局（如果可用）
            self.pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
        except:
            # 回退到spring布局
            self.pos = nx.spring_layout(self.graph, k=3, iterations=50)
        
        # 获取节点属性
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            self.node_colors.append(node_data['color'])
            self.node_sizes.append(node_data['size'])
    
    def create_simple_visualization(self, output_file: str = "citation_tree_simple.png", 
                                  figsize: Tuple[int, int] = (15, 10)):
        """创建简单的网络图可视化"""
        self._add_nodes_to_graph(self.tree_data)
        self._calculate_layout()
        
        plt.figure(figsize=figsize)
        
        # 绘制边
        nx.draw_networkx_edges(self.graph, self.pos, 
                             edge_color='gray', 
                             arrows=True, 
                             arrowsize=20,
                             arrowstyle='-|>',
                             alpha=0.6)
        
        # 绘制节点
        nx.draw_networkx_nodes(self.graph, self.pos,
                             node_color=self.node_colors,
                             node_size=self.node_sizes,
                             alpha=0.8)
        
        # 添加标签
        # 只显示简化的标签（只有标题）
        simple_labels = {}
        for node_id, full_label in self.node_labels.items():
            title = full_label.split('\n')[0]
            if len(title) > 30:
                title = title[:27] + "..."
            simple_labels[node_id] = title
        
        nx.draw_networkx_labels(self.graph, self.pos, 
                              simple_labels,
                              font_size=8,
                              font_color='black')
        
        plt.title("Google Scholar 引用关系图", fontsize=16, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ 简单可视化图已保存到: {output_file}")
    
    def create_detailed_visualization(self, output_file: str = "citation_tree_detailed.png",
                                    figsize: Tuple[int, int] = (20, 15)):
        """创建详细的树形可视化"""
        self._add_nodes_to_graph(self.tree_data)
        
        # 使用层次化布局
        levels = {}
        for node in self.graph.nodes():
            depth = self.graph.nodes[node]['depth']
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(node)
        
        # 手动计算位置
        pos = {}
        y_spacing = 2
        for depth, nodes in levels.items():
            y = -depth * y_spacing
            x_spacing = 4 if len(nodes) > 1 else 0
            x_start = -(len(nodes) - 1) * x_spacing / 2
            
            for i, node in enumerate(nodes):
                x = x_start + i * x_spacing
                pos[node] = (x, y)
        
        self.pos = pos
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # 绘制边
        nx.draw_networkx_edges(self.graph, self.pos, 
                             edge_color='gray', 
                             arrows=True, 
                             arrowsize=15,
                             arrowstyle='-|>',
                             alpha=0.6,
                             ax=ax)
        
        # 绘制节点
        for node in self.graph.nodes():
            x, y = self.pos[node]
            node_data = self.graph.nodes[node]
            
            # 创建节点框
            box = FancyBboxPatch((x-0.8, y-0.3), 1.6, 0.6,
                               boxstyle="round,pad=0.1",
                               facecolor=node_data['color'],
                               edgecolor='black',
                               alpha=0.8)
            ax.add_patch(box)
            
            # 添加文本
            title = node_data['title']
            if len(title) > 40:
                title = title[:37] + "..."
            
            text_lines = [title]
            if node_data['year']:
                text_lines.append(f"({node_data['year']})")
            if node_data['citations'] > 0:
                text_lines.append(f"📊 {node_data['citations']}")
            
            ax.text(x, y, '\n'.join(text_lines), 
                   ha='center', va='center',
                   fontsize=8, fontweight='bold',
                   wrap=True)
        
        ax.set_title("Google Scholar 引用关系树", fontsize=18, fontweight='bold', pad=20)
        ax.axis('off')
        
        # 添加图例
        depth_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
        legend_elements = []
        max_depth = max(self.graph.nodes[node]['depth'] for node in self.graph.nodes())
        
        for depth in range(max_depth + 1):
            color = depth_colors[depth % len(depth_colors)]
            legend_elements.append(plt.Rectangle((0,0),1,1, facecolor=color, 
                                               label=f'深度 {depth}'))
        
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ 详细可视化图已保存到: {output_file}")
    
    def create_statistics_plot(self, output_file: str = "citation_statistics.png"):
        """创建引用统计图表"""
        self._add_nodes_to_graph(self.tree_data)
        
        # 收集统计数据
        depths = []
        citations = []
        years = []
        
        for node in self.graph.nodes():
            node_data = self.graph.nodes[node]
            depths.append(node_data['depth'])
            citations.append(node_data['citations'])
            if node_data['year']:
                try:
                    years.append(int(node_data['year']))
                except:
                    pass
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. 深度分布
        depth_counts = {}
        for d in depths:
            depth_counts[d] = depth_counts.get(d, 0) + 1
        
        ax1.bar(depth_counts.keys(), depth_counts.values(), 
                color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][:len(depth_counts)])
        ax1.set_title('论文按深度分布')
        ax1.set_xlabel('深度')
        ax1.set_ylabel('论文数量')
        
        # 2. 引用次数分布
        ax2.hist(citations, bins=20, color='#45B7D1', alpha=0.7)
        ax2.set_title('引用次数分布')
        ax2.set_xlabel('引用次数')
        ax2.set_ylabel('论文数量')
        
        # 3. 年份分布
        if years:
            ax3.hist(years, bins=min(len(set(years)), 20), color='#96CEB4', alpha=0.7)
            ax3.set_title('发表年份分布')
            ax3.set_xlabel('年份')
            ax3.set_ylabel('论文数量')
        else:
            ax3.text(0.5, 0.5, '无年份数据', ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('发表年份分布')
        
        # 4. 引用次数 vs 深度
        depth_citation_avg = {}
        for d in set(depths):
            depth_citations = [c for i, c in enumerate(citations) if depths[i] == d]
            depth_citation_avg[d] = sum(depth_citations) / len(depth_citations) if depth_citations else 0
        
        ax4.bar(depth_citation_avg.keys(), depth_citation_avg.values(), color='#FFEAA7')
        ax4.set_title('各深度平均引用次数')
        ax4.set_xlabel('深度')
        ax4.set_ylabel('平均引用次数')
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"✅ 统计图表已保存到: {output_file}")
        
        # 打印统计摘要
        print("\n📊 统计摘要:")
        print(f"   总论文数: {len(depths)}")
        print(f"   最大深度: {max(depths) if depths else 0}")
        print(f"   平均引用次数: {sum(citations)/len(citations):.1f}")
        print(f"   最高引用次数: {max(citations) if citations else 0}")
        if years:
            print(f"   年份范围: {min(years)} - {max(years)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Google Scholar 引用树可视化工具")
    parser.add_argument("json_file", help="引用树JSON文件路径")
    parser.add_argument("--type", choices=['simple', 'detailed', 'stats', 'all'], 
                       default='all', help="可视化类型")
    parser.add_argument("--output", help="输出文件前缀", default="visualization")
    
    args = parser.parse_args()
    
    try:
        visualizer = CitationTreeVisualizer(args.json_file)
        
        print(f"🎨 开始创建可视化图表...")
        print(f"📁 输入文件: {args.json_file}")
        print(f"🎯 可视化类型: {args.type}")
        print("-" * 50)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(args.output) if os.path.dirname(args.output) else "."
        if output_dir != "." and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"📁 创建输出目录: {output_dir}")
        
        if args.type == 'simple' or args.type == 'all':
            visualizer.create_simple_visualization(f"{args.output}_simple.png")
        
        if args.type == 'detailed' or args.type == 'all':
            visualizer.create_detailed_visualization(f"{args.output}_detailed.png")
        
        if args.type == 'stats' or args.type == 'all':
            visualizer.create_statistics_plot(f"{args.output}_stats.png")
        
        print("\n✅ 所有可视化图表创建完成!")
        
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {args.json_file}")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()
