#!/bin/bash

# Google Scholar 引用爬虫 - 一键运行脚本
# 用法: ./run_all.sh

echo "🕷️  Google Scholar 引用爬虫 - 一键运行"
echo "============================================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3"
    exit 1
fi

echo "✅ Python环境检查通过"

# 安装依赖
echo ""
echo "📦 安装依赖包..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖安装完成"

# 运行基本测试
echo ""
echo "🧪 运行基本功能测试..."
python test_crawler.py --test

if [ $? -ne 0 ]; then
    echo "❌ 基本测试失败"
    exit 1
fi

echo "✅ 基本测试通过"

# 创建可视化（如果有JSON文件）
echo ""
echo "🎨 创建可视化图表..."

JSON_FILE="test_citation_tree.json"
if [ -f "$JSON_FILE" ]; then
    echo "找到测试数据文件: $JSON_FILE"
    python visualize_tree.py "$JSON_FILE" --type all --output test_visualization
    
    if [ $? -eq 0 ]; then
        echo "✅ 可视化创建成功"
        echo "📁 生成的文件:"
        ls -la test_visualization_*.png 2>/dev/null || echo "   (未找到图像文件)"
    else
        echo "⚠️  可视化创建失败，但不影响主要功能"
    fi
else
    echo "⚠️  未找到测试数据文件，跳过可视化"
fi

echo ""
echo "✅ 所有测试完成!"
echo "============================================================"
echo ""
echo "🎯 接下来你可以:"
echo "   1. 运行演示:         python demo.py --demo"
echo "   2. 交互式测试:       python test_crawler.py --interactive"
echo "   3. 查看帮助:         python demo.py --help"
echo "   4. 阅读文档:         cat README.md"
echo ""
echo "📊 项目文件结构:"
ls -la *.py *.txt *.md 2>/dev/null
echo ""
echo "🎉 安装和测试完成!"
