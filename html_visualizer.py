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
        :root {
            --bg-color: #f8f9fa;
            --card-bg: #ffffff;
            --text-color: #2c3e50;
            --text-secondary: #7f8c8d;
            --primary-color: #3498db;
            --primary-dark: #2980b9;
            --header-color: #2c3e50;
            --control-bg: #ecf0f1;
            --border-color: #bdc3c7;
            --tooltip-bg: rgba(0, 0, 0, 0.9);
            --tooltip-text: #ffffff;
            --node-stroke: #ffffff;
            --shadow-color: rgba(0,0,0,0.1);
            --link-color: #999;
            --highlight-color: #e74c3c;
        }
        
        body.dark-theme {
            --bg-color: #1e272e;
            --card-bg: #2d3436;
            --text-color: #dfe6e9;
            --text-secondary: #b2bec3;
            --primary-color: #00a8ff;
            --primary-dark: #0097e6;
            --header-color: #dfe6e9;
            --control-bg: #2d3436;
            --border-color: #636e72;
            --tooltip-bg: rgba(45, 52, 54, 0.95);
            --tooltip-text: #dfe6e9;
            --node-stroke: #2d3436;
            --shadow-color: rgba(0,0,0,0.3);
            --link-color: #b2bec3;
            --highlight-color: #ff7675;
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
            transition: background-color 0.3s ease, color 0.3s ease;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px var(--shadow-color);
        }
        
        .header h1 {
            color: var(--header-color);
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }
        
        .header p {
            color: var(--text-secondary);
            margin: 0;
            font-size: 1.1em;
        }
        
        .container {
            background: var(--card-bg);
            border-radius: 10px;
            box-shadow: 0 2px 10px var(--shadow-color);
            overflow: hidden;
        }
        
        .controls {
            padding: 20px;
            background: var(--control-bg);
            border-bottom: 1px solid var(--border-color);
        }
        
        .control-group {
            display: inline-block;
            margin-right: 20px;
        }
        
        .control-group label {
            display: inline-block;
            margin-right: 10px;
            font-weight: bold;
            color: var(--text-color);
        }
        
        button {
            background: var(--primary-color);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s, transform 0.1s;
        }
        
        button:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
        }
        
        #depth-controls {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed var(--border-color);
        }
        
        #depthSelector {
            padding: 8px;
            border-radius: 5px;
            border: 1px solid var(--border-color);
            margin-right: 10px;
            background-color: var(--card-bg);
            color: var(--text-color);
            font-size: 14px;
        }
        
        #theme-toggle {
            position: absolute;
            top: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            font-size: 20px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 5px var(--shadow-color);
            z-index: 1000;
            transition: background 0.3s, transform 0.1s;
        }
        
        #theme-toggle:hover {
            background: var(--primary-dark);
            transform: scale(1.1);
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
            stroke: var(--node-stroke);
            stroke-width: 2px;
            transition: stroke 0.3s, stroke-width 0.3s;
        }
        
        .node-circle.has-children {
            cursor: pointer;
        }
        
        .node-circle.has-children:hover {
            stroke: var(--highlight-color);
            stroke-width: 3px;
        }
        
        .node-text {
            font-size: 12px;
            text-anchor: middle;
            pointer-events: none;
            font-weight: bold;
            fill: var(--text-color);
            transition: fill 0.3s;
        }
        
        .link {
            fill: none;
            stroke: var(--link-color);
            stroke-width: 2px;
            stroke-opacity: 0.6;
            marker-end: url(#arrowhead);
            transition: stroke 0.3s;
        }
        
        .tooltip {
            position: absolute;
            background: var(--tooltip-bg);
            color: var(--tooltip-text);
            padding: 15px;
            border-radius: 8px;
            font-size: 14px;
            max-width: 400px;
            pointer-events: none;
            z-index: 1000;
            box-shadow: 0 4px 20px var(--shadow-color);
            line-height: 1.4;
            transition: background 0.3s, color 0.3s;
        }
        
        .tooltip .title {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 8px;
            color: var(--primary-color);
        }
        
        .tooltip .authors {
            color: var(--text-secondary);
            margin-bottom: 5px;
        }
        
        .tooltip .year {
            color: #f39c12;
            margin-bottom: 5px;
        }
        
        .tooltip .citations {
            color: var(--highlight-color);
            margin-bottom: 8px;
        }
        
        .tooltip .abstract {
            font-size: 12px;
            color: var(--tooltip-text);
            max-height: 100px;
            overflow-y: auto;
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border-color);
        }
        
        .depth-legend {
            position: absolute;
            top: 20px;
            right: 70px;
            background: var(--card-bg);
            color: var(--text-color);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px var(--shadow-color);
            transition: background 0.3s, color 0.3s;
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
            border: 2px solid var(--card-bg);
            transition: border-color 0.3s;
        }
        
        .stats {
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: var(--card-bg);
            color: var(--text-color);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px var(--shadow-color);
            font-size: 14px;
            transition: background 0.3s, color 0.3s;
        }
        
        .highlight {
            stroke: var(--highlight-color) !important;
            stroke-width: 4px !important;
        }
        
        .usage-tip {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--card-bg);
            color: var(--text-color);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px var(--shadow-color);
            font-size: 14px;
            z-index: 1000;
            max-width: 300px;
            border: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            transition: opacity 0.5s ease, background-color 0.3s;
        }
        
        .usage-tip h4 {
            margin-top: 0;
            margin-bottom: 10px;
            color: var(--header-color);
        }
        
        .usage-tip ul {
            margin: 0;
            padding-left: 20px;
        }
        
        .usage-tip li {
            margin-bottom: 5px;
        }
        
        .usage-tip button {
            align-self: flex-end;
            margin-top: 10px;
            padding: 5px 10px;
            background: var(--control-bg);
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }
    </style>
</head>
<body>
    <button id="theme-toggle" title="切换深色/浅色主题">🌓</button>
    
    <div class="header">
        <h1>🕷️ 论文引用关系可视化</h1>
        <p>鼠标悬停查看详情，点击节点展开/折叠，按住Command键(Mac)或Ctrl键(Windows/Linux)点击节点访问论文链接</p>
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
            <div class="control-group" id="depth-controls">
                <label>按层级操作:</label>
                <select id="depthSelector"></select>
                <button onclick="expandToLevel()">展开到此层</button>
                <button onclick="collapseToLevel()">折叠到此层</button>
            </div>
        </div>
        
        <div id="visualization"></div>
    </div>
    
    <div class="depth-legend">
        <h4 style="margin: 0 0 10px 0; color: var(--header-color);">深度图例</h4>
        <div id="legend-items"></div>
    </div>
    
    <div class="stats">
        <h4 style="margin: 0 0 10px 0; color: var(--header-color);">统计信息</h4>
        <div id="stats-content"></div>
    </div>
    
    <div id="usage-tip" class="usage-tip">
        <h4>📝 操作指南</h4>
        <ul>
            <li><strong>点击节点</strong>：展开或折叠节点</li>
            <li><strong>按住Command/Ctrl+点击</strong>：打开论文链接</li>
            <li><strong>点击+/-符号</strong>：展开或折叠特定节点</li>
            <li><strong>使用下拉菜单</strong>：按层级展开/折叠</li>
        </ul>
        <button onclick="hideUsageTip()">我知道了</button>
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
        let collapsedNodes = new Set(); // 存储折叠节点的ID
        
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
                .attr("fill", "var(--link-color)");
            
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
            
            // 填充深度选择器
            populateDepthSelector();
            
            // 默认使用树形布局
            drawTreeLayout();
        }
        
        function drawTreeLayout() {
            currentLayout = 'tree';
            
            // 清除现有内容
            g.selectAll("*").remove();
            
            // 应用树形布局
            // 首先需要处理节点的折叠状态
            processNodeCollapse(root);
            
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
                .attr("class", d => (d._children || d.children) ? "node-circle has-children" : "node-circle")
                .attr("r", d => 15 + Math.sqrt(d.data.citation_count) * 2)
                .style("fill", d => depthColors[d.data.depth % depthColors.length])
                .on("mouseover", showTooltip)
                .on("mousemove", moveTooltip)
                .on("mouseout", hideTooltip)
                .on("click", function(event, d) {
                    // 检查是否按住了Command键(Mac)或Ctrl键(Windows/Linux)
                    if (event.metaKey || event.ctrlKey) {
                        // 按住特殊键时，打开论文链接
                        openPaperUrl(event, d);
                    } else {
                        // 没按住特殊键时，执行展开/折叠操作
                        if (d._children || d.children) {
                            // 切换节点的折叠状态
                            toggleNode(d);
                            // 重绘树形布局
                            drawTreeLayout();
                        }
                    }
                });
            
            // 添加节点文本
            nodes.append("text")
                .attr("class", "node-text")
                .attr("dy", "0.35em")
                .attr("x", d => d.children || d._children ? -25 : 25)
                .style("text-anchor", d => d.children || d._children ? "end" : "start")
                .text(d => {
                    const title = d.data.title;
                    return title.length > 20 ? title.substring(0, 20) + "..." : title;
                });
                
            // 为有子节点的节点添加展开/折叠指示器
            nodes.filter(d => d._children || d.children)
                .append("text")
                .attr("class", "node-text")
                .attr("dy", "0.35em")
                .attr("x", -15)
                .attr("y", 0)
                .style("text-anchor", "middle")
                .style("font-weight", "bold")
                .style("font-size", "16px")
                .style("cursor", "pointer")
                .text(d => d.children ? "−" : "+")
                .on("click", function(event, d) {
                    event.stopPropagation();
                    toggleNode(d);
                    drawTreeLayout();
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
                .attr("class", "link")
                .style("stroke", "var(--link-color)");
            
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
                .on("click", function(event, d) {
                    // 在力导向布局中，只有按住Command键(Mac)或Ctrl键(Windows/Linux)时才打开链接
                    if (event.metaKey || event.ctrlKey) {
                        openPaperUrl(event, d);
                    }
                });
            
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
        
        // 处理节点的折叠状态
        function processNodeCollapse(node) {
            if (collapsedNodes.has(node.data.id)) {
                // 如果节点是折叠的，暂存其子节点并移除
                node._children = node.children;
                node.children = null;
            } else if (node._children) {
                // 如果节点是展开的，恢复其子节点
                node.children = node._children;
                node._children = null;
            }
            
            // 递归处理子节点
            if (node.children) {
                node.children.forEach(child => processNodeCollapse(child));
            }
            return node;
        }
        
        // 切换节点的折叠状态
        function toggleNode(d) {
            if (d.children) {
                // 如果有可见的子节点，则折叠
                collapsedNodes.add(d.data.id);
            } else {
                // 如果节点已折叠，则展开
                collapsedNodes.delete(d.data.id);
            }
        }
        
        // 填充深度选择器
        function populateDepthSelector() {
            const depthSelector = document.getElementById("depthSelector");
            depthSelector.innerHTML = "";
            
            const maxDepth = d3.max(root.descendants(), d => d.data.depth);
            
            for (let i = 0; i <= maxDepth; i++) {
                const option = document.createElement("option");
                option.value = i;
                option.text = `层级 ${i}`;
                depthSelector.appendChild(option);
            }
        }
        
        // 根据深度展开节点
        function expandToLevel() {
            if (currentLayout === 'force') {
                changeLayout('tree');
            }
            
            const selectedDepth = parseInt(document.getElementById("depthSelector").value);
            
            // 遍历所有节点，展开到指定深度
            collapsedNodes.clear(); // 先清空所有折叠状态
            
            // 遍历并标记应该折叠的节点
            root.descendants().forEach(node => {
                if (node.data.depth > selectedDepth) {
                    // 找到其父节点并将其折叠
                    const parent = findParentAtDepth(node, selectedDepth);
                    if (parent) {
                        collapsedNodes.add(parent.data.id);
                    }
                }
            });
            
            drawTreeLayout();
        }
        
        // 根据深度折叠节点
        function collapseToLevel() {
            if (currentLayout === 'force') {
                changeLayout('tree');
            }
            
            const selectedDepth = parseInt(document.getElementById("depthSelector").value);
            
            // 清除所有折叠状态
            collapsedNodes.clear();
            
            // 折叠所有指定深度的节点
            root.descendants().forEach(node => {
                if (node.data.depth === selectedDepth) {
                    collapsedNodes.add(node.data.id);
                }
            });
            
            drawTreeLayout();
        }
        
        // 找到特定深度的父节点
        function findParentAtDepth(node, targetDepth) {
            let current = node;
            
            // 向上寻找直到找到目标深度的节点
            while (current.parent && current.data.depth > targetDepth) {
                current = current.parent;
            }
            
            return current.data.depth === targetDepth ? current : null;
        }
        
        // 展开所有节点
        function expandAll() {
            if (currentLayout === 'tree') {
                collapsedNodes.clear();
                drawTreeLayout();
            }
        }
        
        // 折叠所有节点（除了根节点）
        function collapseAll() {
            if (currentLayout === 'tree') {
                collapsedNodes.clear();
                
                // 获取所有非叶节点
                root.descendants().forEach(node => {
                    if (node.data.depth > 0 && (node.children || node._children)) {
                        collapsedNodes.add(node.data.id);
                    }
                });
                
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
        
        // 提示框管理
        function hideUsageTip() {
            document.getElementById('usage-tip').style.opacity = '0';
            setTimeout(() => {
                document.getElementById('usage-tip').style.display = 'none';
            }, 500);
            
            // 保存用户已看过提示的状态到localStorage
            localStorage.setItem('papertracer_tip_shown', 'true');
        }
        
        function checkTipVisibility() {
            // 如果用户之前已经看过提示，则不再显示
            if (localStorage.getItem('papertracer_tip_shown')) {
                document.getElementById('usage-tip').style.display = 'none';
            }
        }
        
        // 主题管理
        function toggleTheme() {
            const body = document.body;
            const isDarkMode = body.classList.toggle('dark-theme');
            
            // 保存主题设置到localStorage
            localStorage.setItem('papertracer_dark_theme', isDarkMode);
            
            // 需要重绘图表以适应新主题
            if (currentLayout === 'tree') {
                drawTreeLayout();
            } else {
                drawForceLayout();
            }
            
            // 更新箭头颜色
            updateArrowheadColor();
        }
        
        function updateArrowheadColor() {
            // 在深色模式下，更改箭头颜色
            const isDarkMode = document.body.classList.contains('dark-theme');
            const arrowColor = isDarkMode ? '#b2bec3' : '#999';
            
            d3.select("#arrowhead path")
                .attr("fill", arrowColor);
        }
        
        function checkThemePreference() {
            // 检查用户偏好或保存的设置
            const savedTheme = localStorage.getItem('papertracer_dark_theme');
            
            // 如果有保存的设置，应用保存的设置
            if (savedTheme === 'true') {
                document.body.classList.add('dark-theme');
                return;
            }
            
            // 如果没有保存的设置，检查系统偏好
            const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDarkMode) {
                document.body.classList.add('dark-theme');
            }
        }
        
        // 添加主题切换按钮监听
        document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
        
        // 初始化页面
        // 添加主题变化监听器
        const darkModeMediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        darkModeMediaQuery.addEventListener('change', e => {
            const isSystemDark = e.matches;
            if (isSystemDark && !document.body.classList.contains('dark-theme')) {
                toggleTheme();
            } else if (!isSystemDark && document.body.classList.contains('dark-theme')) {
                toggleTheme();
            }
        });
        
        checkThemePreference(); // 检查主题偏好
        init();
        // 检查是否需要显示提示
        checkTipVisibility();
        // 应用正确的箭头颜色
        updateArrowheadColor();
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
        print(f"   - 🌲 支持按层级展开和折叠节点")
        
    except Exception as e:
        print(f"❌ 创建HTML可视化时出错: {e}")
        return False
        
    return True

if __name__ == "__main__":
    main()
