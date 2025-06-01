#!/usr/bin/env python3
"""
交互式HTML可视化工具
使用D3.js创建可交互的论文引用关系可视化页面
"""

import json
import os
from typing import Dict, List
from papertracer_config import Config


class InteractiveHTMLVisualizer:
    """交互式HTML可视化器"""
    
    def __init__(self, json_file: str):
        """初始化可视化器"""
        with open(json_file, 'r', encoding='utf-8') as f:
            self.tree_data = json.load(f)
        self.node_counter = 0
    
    def _process_node(self, node_data: Dict) -> Dict:
        """处理节点数据，添加唯一ID和格式化"""
        self.node_counter += 1
        paper = node_data['paper']
        
        # 创建处理后的节点
        processed_node = {
            'id': f"node_{self.node_counter}",
            'title': paper['title'] if paper['title'] else "Unknown Title",
            'authors': paper['authors'] if paper['authors'] else "Unknown Authors", 
            'year': paper['year'] if paper['year'] else "Unknown Year",
            'citation_count': paper['citation_count'],
            'url': paper['url'] if paper['url'] else "#",
            'cited_by_url': paper['cited_by_url'] if paper['cited_by_url'] else "#",
            'abstract': paper['abstract'] if paper['abstract'] else "No abstract available",
            'depth': node_data['depth'],
            'children': []
        }
        
        # 递归处理子节点
        for child in node_data['children']:
            processed_child = self._process_node(child)
            processed_node['children'].append(processed_child)
        
        return processed_node
    
    def create_interactive_html(self, output_file: str = "interactive_citation_tree.html"):
        """创建交互式HTML可视化页面"""
        
        # 处理数据
        processed_data = self._process_node(self.tree_data)
        
        # 生成HTML模板
        html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>论文引用关系可视化</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2c3e50;
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }
        
        .header p {
            color: #7f8c8d;
            margin: 0;
            font-size: 1.1em;
        }
        
        .container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .controls {
            padding: 20px;
            background: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
        }
        
        .control-group {
            display: inline-block;
            margin-right: 20px;
        }
        
        .control-group label {
            display: inline-block;
            margin-right: 10px;
            font-weight: bold;
            color: #34495e;
        }
        
        button {
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        
        button:hover {
            background: #2980b9;
        }
        
        #visualization {
            position: relative;
            overflow: hidden;
        }
        
        .node {
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .node:hover {
            filter: brightness(1.1);
        }
        
        .node-circle {
            stroke: #fff;
            stroke-width: 2px;
        }
        
        .node-text {
            font-size: 12px;
            text-anchor: middle;
            pointer-events: none;
            font-weight: bold;
        }
        
        .link {
            fill: none;
            stroke: #999;
            stroke-width: 2px;
            stroke-opacity: 0.6;
            marker-end: url(#arrowhead);
        }
        
        .tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            max-width: 400px;
            pointer-events: none;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            line-height: 1.4;
        }
        
        .tooltip .title {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
            color: #3498db;
        }
        
        .tooltip .authors {
            color: #95a5a6;
            margin-bottom: 5px;
        }
        
        .tooltip .year {
            color: #f39c12;
            margin-bottom: 5px;
        }
        
        .tooltip .citations {
            color: #e74c3c;
            margin-bottom: 8px;
        }
        
        .tooltip .abstract {
            font-size: 12px;
            color: #ecf0f1;
            max-height: 100px;
            overflow-y: auto;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #555;
        }
        
        .depth-legend {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 10px;
            border: 2px solid #fff;
        }
        
        .stats {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            font-size: 14px;
        }
        
        .highlight {
            stroke: #e74c3c !important;
            stroke-width: 4px !important;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🕷️ 论文引用关系可视化</h1>
        <p>鼠标悬停查看详情，点击节点访问论文链接</p>
    </div>
    
    <div class="container">
        <div class="controls">
            <div class="control-group">
                <button onclick="resetZoom()">重置视图</button>
                <button onclick="expandAll()">展开所有</button>
                <button onclick="collapseAll()">折叠所有</button>
            </div>
            <div class="control-group">
                <label>布局类型:</label>
                <button onclick="changeLayout('tree')">树形</button>
                <button onclick="changeLayout('force')">力导向</button>
            </div>
        </div>
        
        <div id="visualization"></div>
    </div>
    
    <div class="depth-legend">
        <h4 style="margin: 0 0 10px 0; color: #2c3e50;">深度图例</h4>
        <div id="legend-items"></div>
    </div>
    
    <div class="stats">
        <h4 style="margin: 0 0 10px 0; color: #2c3e50;">统计信息</h4>
        <div id="stats-content"></div>
    </div>

    <script>
        // 数据
        const treeData = ''' + json.dumps(processed_data, ensure_ascii=False, indent=2) + ''';
        
        // 配置
        const width = window.innerWidth - 40;
        const height = window.innerHeight - 200;
        const depthColors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
        
        let currentLayout = 'tree';
        let svg, g, root, tooltip;
        let tree, force;
        
        // 初始化
        function init() {
            // 创建SVG
            svg = d3.select("#visualization")
                .append("svg")
                .attr("width", width)
                .attr("height", height)
                .call(d3.zoom().on("zoom", function(event) {
                    g.attr("transform", event.transform);
                }));
            
            // 定义箭头标记
            svg.append("defs").append("marker")
                .attr("id", "arrowhead")
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 15)
                .attr("refY", 0)
                .attr("orient", "auto")
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("fill", "#999");
            
            g = svg.append("g");
            
            // 创建工具提示
            tooltip = d3.select("body").append("div")
                .attr("class", "tooltip")
                .style("opacity", 0);
            
            // 初始化树形布局
            tree = d3.tree().size([height - 100, width - 200]);
            
            // 初始化力导向布局
            force = d3.forceSimulation()
                .force("link", d3.forceLink().id(d => d.id))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2));
            
            // 处理数据
            root = d3.hierarchy(treeData);
            
            // 生成图例和统计信息
            generateLegend();
            generateStats();
            
            // 默认使用树形布局
            drawTreeLayout();
        }
        
        function drawTreeLayout() {
            currentLayout = 'tree';
            
            // 清除现有内容
            g.selectAll("*").remove();
            
            // 应用树形布局
            tree(root);
            
            // 绘制连接线
            const links = g.selectAll(".link")
                .data(root.links())
                .enter().append("path")
                .attr("class", "link")
                .attr("d", d3.linkHorizontal()
                    .x(d => d.y)
                    .y(d => d.x));
            
            // 绘制节点
            const nodes = g.selectAll(".node")
                .data(root.descendants())
                .enter().append("g")
                .attr("class", "node")
                .attr("transform", d => `translate(${d.y},${d.x})`);
            
            // 添加节点圆圈
            nodes.append("circle")
                .attr("class", "node-circle")
                .attr("r", d => 15 + Math.sqrt(d.data.citation_count) * 2)
                .style("fill", d => depthColors[d.data.depth % depthColors.length])
                .on("mouseover", showTooltip)
                .on("mousemove", moveTooltip)
                .on("mouseout", hideTooltip)
                .on("click", openPaperUrl);
            
            // 添加节点文本
            nodes.append("text")
                .attr("class", "node-text")
                .attr("dy", "0.35em")
                .attr("x", d => d.children ? -25 : 25)
                .style("text-anchor", d => d.children ? "end" : "start")
                .text(d => {
                    const title = d.data.title;
                    return title.length > 20 ? title.substring(0, 20) + "..." : title;
                });
        }
        
        function drawForceLayout() {
            currentLayout = 'force';
            
            // 清除现有内容
            g.selectAll("*").remove();
            
            // 转换为节点和连接数据
            const nodes = root.descendants().map(d => ({...d.data, fx: null, fy: null}));
            const links = root.links().map(d => ({
                source: d.source.data.id,
                target: d.target.data.id
            }));
            
            // 绘制连接线
            const linkElements = g.selectAll(".link")
                .data(links)
                .enter().append("line")
                .attr("class", "link");
            
            // 绘制节点
            const nodeElements = g.selectAll(".node")
                .data(nodes)
                .enter().append("g")
                .attr("class", "node")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // 添加节点圆圈
            nodeElements.append("circle")
                .attr("class", "node-circle")
                .attr("r", d => 15 + Math.sqrt(d.citation_count) * 2)
                .style("fill", d => depthColors[d.depth % depthColors.length])
                .on("mouseover", showTooltip)
                .on("mousemove", moveTooltip)
                .on("mouseout", hideTooltip)
                .on("click", openPaperUrl);
            
            // 添加节点文本
            nodeElements.append("text")
                .attr("class", "node-text")
                .attr("dy", "0.35em")
                .text(d => {
                    const title = d.title;
                    return title.length > 15 ? title.substring(0, 15) + "..." : title;
                });
            
            // 启动力导向仿真
            force.nodes(nodes)
                .force("link").links(links);
            
            force.on("tick", () => {
                linkElements
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);
                
                nodeElements
                    .attr("transform", d => `translate(${d.x},${d.y})`);
            });
            
            force.restart();
        }
        
        function showTooltip(event, d) {
            const data = currentLayout === 'tree' ? d.data : d;
            tooltip.transition().duration(200).style("opacity", .9);
            
            let tooltipContent = `
                <div class="title">${data.title}</div>
                <div class="authors">👥 ${data.authors}</div>
                <div class="year">📅 ${data.year}</div>
                <div class="citations">📊 被引用 ${data.citation_count} 次</div>
            `;
            
            if (data.abstract && data.abstract !== "No abstract available") {
                tooltipContent += `<div class="abstract">${data.abstract}</div>`;
            }
            
            tooltip.html(tooltipContent);
        }
        
        function moveTooltip(event) {
            tooltip
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 10) + "px");
        }
        
        function hideTooltip() {
            tooltip.transition().duration(500).style("opacity", 0);
        }
        
        function openPaperUrl(event, d) {
            const data = currentLayout === 'tree' ? d.data : d;
            if (data.url && data.url !== "#") {
                window.open(data.url, '_blank');
            } else if (data.cited_by_url && data.cited_by_url !== "#") {
                window.open(data.cited_by_url, '_blank');
            }
        }
        
        function changeLayout(layout) {
            if (layout === 'tree') {
                drawTreeLayout();
            } else if (layout === 'force') {
                drawForceLayout();
            }
        }
        
        function resetZoom() {
            svg.transition().duration(750).call(
                d3.zoom().transform,
                d3.zoomIdentity
            );
        }
        
        function expandAll() {
            // 树形布局的展开折叠功能可以在这里实现
            if (currentLayout === 'tree') {
                drawTreeLayout();
            }
        }
        
        function collapseAll() {
            // 树形布局的展开折叠功能可以在这里实现
            if (currentLayout === 'tree') {
                drawTreeLayout();
            }
        }
        
        function generateLegend() {
            const legendContainer = d3.select("#legend-items");
            const maxDepth = d3.max(root.descendants(), d => d.data.depth);
            
            for (let i = 0; i <= maxDepth; i++) {
                const legendItem = legendContainer.append("div")
                    .attr("class", "legend-item");
                
                legendItem.append("div")
                    .attr("class", "legend-color")
                    .style("background-color", depthColors[i % depthColors.length]);
                
                legendItem.append("span")
                    .text(`深度 ${i}`);
            }
        }
        
        function generateStats() {
            const nodes = root.descendants();
            const totalPapers = nodes.length;
            const totalCitations = d3.sum(nodes, d => d.data.citation_count);
            const maxDepth = d3.max(nodes, d => d.data.depth);
            const avgCitations = totalCitations / totalPapers;
            
            const statsContent = `
                <div>📄 总论文数: ${totalPapers}</div>
                <div>📊 总引用数: ${totalCitations}</div>
                <div>📏 最大深度: ${maxDepth}</div>
                <div>📈 平均引用: ${avgCitations.toFixed(1)}</div>
            `;
            
            d3.select("#stats-content").html(statsContent);
        }
        
        // 拖拽功能（仅用于力导向布局）
        function dragstarted(event, d) {
            if (!event.active) force.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) force.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        // 窗口大小调整
        window.addEventListener('resize', function() {
            const newWidth = window.innerWidth - 40;
            const newHeight = window.innerHeight - 200;
            
            svg.attr("width", newWidth).attr("height", newHeight);
            
            if (currentLayout === 'tree') {
                tree.size([newHeight - 100, newWidth - 200]);
                drawTreeLayout();
            } else {
                force.force("center", d3.forceCenter(newWidth / 2, newHeight / 2));
                force.restart();
            }
        });
        
        // 初始化页面
        init();
    </script>
</body>
</html>'''
        
        # 保存HTML文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        print(f"✅ 交互式HTML可视化已保存到: {output_file}")
        print(f"🌐 请在浏览器中打开此文件查看交互式可视化")
        
        return output_file

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="创建交互式HTML论文引用可视化")
    parser.add_argument("json_file", help="引用树JSON文件路径")
    parser.add_argument("--output", help="输出HTML文件路径", default="interactive_citation_tree.html")
    
    args = parser.parse_args()
    
    try:
        visualizer = InteractiveHTMLVisualizer(args.json_file)
        output_file = visualizer.create_interactive_html(args.output)
        
        print(f"\n🎉 成功创建交互式可视化!")
        print(f"📁 输出文件: {output_file}")
        print(f"💡 功能特性:")
        print(f"   - 🖱️  鼠标悬停显示论文详细信息")
        print(f"   - 🔗 点击节点访问论文链接")
        print(f"   - 🎛️  支持树形和力导向两种布局")
        print(f"   - 🔍 支持缩放和拖拽")
        print(f"   - 📊 显示统计信息和深度图例")
        
    except Exception as e:
        print(f"❌ 创建HTML可视化时出错: {e}")
        return False
        
    return True

if __name__ == "__main__":
    main()
