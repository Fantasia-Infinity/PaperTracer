# 🕷️ Google Scholar 引用爬虫 - 使用指南

## 🎯 系统功能概述

你现在拥有一个功能完整的Google Scholar引用爬虫系统，它可以：

1. **递归爬取引用关系** - 从一篇文章开始，递归爬取所有引用它的文章
2. **构建树形数据结构** - 将引用关系组织成清晰的树形结构
3. **智能文件管理** - 自动创建输出目录，使用时间戳命名避免覆盖
4. **数据导出与保存** - 支持JSON格式导出到专门的输出目录
5. **可视化展示** - 生成多种类型的可视化图表
6. **统计分析** - 提供详细的统计信息和分析

## 📁 输出文件管理

### 自动目录创建
系统会自动创建 `output/` 目录来存放所有生成的文件：

```
output/
├── demo_20250601_143052_citation_tree.json    # 引用数据
├── demo_20250601_143052_simple.png            # 简单网络图
├── demo_20250601_143052_stats.png             # 统计图表
└── README.md                                   # 目录说明
```

### 时间戳命名
- 格式: `demo_YYYYMMDD_HHMMSS_类型.扩展名`
- 好处: 避免覆盖、保留历史记录、便于管理

## 🚀 快速开始

### 方法1: 使用演示脚本（推荐新手）
```bash
# 运行完整演示
python demo.py --demo

# 查看帮助
python demo.py --help
```

### 方法2: 使用测试工具（交互式配置）
```bash
# 基本功能测试
python test_crawler.py --test

# 交互式配置测试
python test_crawler.py --interactive
```

### 方法3: 直接使用爬虫模块（高级用户）
```python
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json

# 创建爬虫实例
crawler = GoogleScholarCrawler(
    max_depth=3,              # 递归深度
    max_papers_per_level=10,  # 每层最多论文数
    delay_range=(1, 3)        # 请求间隔
)

# 爬取引用树
url = "你的Google Scholar引用链接"
tree = crawler.build_citation_tree(url)

# 显示和保存结果
if tree:
    print_citation_tree(tree)
    save_tree_to_json(tree, "my_citation_tree.json")
```

## 📊 可视化功能

### 创建网络图
```bash
python visualize_tree.py your_tree.json --type simple
```

### 创建详细的层次图
```bash
python visualize_tree.py your_tree.json --type detailed
```

### 创建统计图表
```bash
python visualize_tree.py your_tree.json --type stats
```

### 创建所有类型的图表
```bash
python visualize_tree.py your_tree.json --type all
```

## 🔗 如何获取Google Scholar链接

1. 在Google Scholar中搜索目标论文
2. 找到论文条目，点击下方的 "Cited by X" 链接
3. 复制浏览器地址栏中的完整URL
4. 确保URL包含 `cites=` 参数

示例URL格式：
```
https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en
```

## ⚙️ 参数配置建议

### 小规模测试（适合首次使用）
```python
max_depth=2
max_papers_per_level=3
delay_range=(1, 2)
```

### 中等规模研究
```python
max_depth=3
max_papers_per_level=10
delay_range=(1, 3)
```

### 大规模学术分析
```python
max_depth=4
max_papers_per_level=20
delay_range=(2, 5)
```

## 📁 生成的文件说明

### JSON数据文件
- 包含完整的引用树数据结构
- 可用于后续分析和处理
- 支持跨平台和跨语言使用

### PNG可视化图片
- `*_simple.png` - 简单的网络关系图
- `*_detailed.png` - 详细的层次结构图
- `*_stats.png` - 统计分析图表

## 💡 使用技巧

### 1. 批量处理多个论文
```python
urls = [
    "paper1_cites_url",
    "paper2_cites_url",
    "paper3_cites_url"
]

for i, url in enumerate(urls):
    tree = crawler.build_citation_tree(url)
    if tree:
        save_tree_to_json(tree, f"paper_{i}_citations.json")
```

### 2. 数据分析示例
```python
import json

# 读取保存的数据
with open("citation_tree.json", "r") as f:
    data = json.load(f)

# 分析函数
def analyze_citations(node, depth=0):
    paper = node["paper"]
    print(f"{'  ' * depth}{paper['title']} ({paper['citation_count']} citations)")
    
    for child in node["children"]:
        analyze_citations(child, depth + 1)

analyze_citations(data)
```

### 3. 合并多个引用树
```python
def merge_citation_trees(trees):
    # 你的合并逻辑
    pass
```

## ⚠️ 重要注意事项

### 1. 遵守使用规范
- 遵守Google Scholar的服务条款
- 设置合适的请求间隔，避免过于频繁的访问
- 尊重网站的robots.txt文件

### 2. 网络稳定性
- 确保网络连接稳定
- 大规模爬取建议在网络条件良好时进行
- 可以设置更长的延迟时间来提高成功率

### 3. 数据质量
- 某些论文可能解析不完整（显示为"Unknown Title"）
- 引用次数可能存在时差
- 建议定期更新数据

### 4. 性能考虑
- 递归深度越大，爬取时间越长
- 每层论文数量直接影响总体规模
- 建议从小规模开始测试

## 🔧 故障排除

### 常见问题及解决方案

**Q: 爬虫返回空结果？**
A: 检查URL格式，确保网络连接，尝试增加延迟时间

**Q: 可视化功能报错？**
A: 确保安装了所有依赖：`pip install matplotlib networkx`

**Q: 速度太慢？**
A: 减少递归深度和每层论文数量，或者增加更多并行处理

**Q: 被反爬虫机制阻止？**
A: 增加延迟时间，更换User-Agent，或者分批处理

## 📈 扩展功能建议

### 1. 数据库集成
可以将结果保存到数据库中，支持更复杂的查询和分析

### 2. 网络分析
使用NetworkX进行更深入的网络分析，如中心性分析、社群发现等

### 3. 时间序列分析
跟踪引用关系的时间演变，分析学术影响力的变化

### 4. 多源数据整合
结合其他学术数据库的信息，构建更完整的学术网络

## 🗂️ 输出文件管理工具

### 查看输出文件
```bash
# 列出所有输出文件及其详细信息
python clean_output.py list
```

### 清理旧文件
```bash
# 预览7天前的文件（不会实际删除）
python clean_output.py clean --days 7

# 确认删除7天前的文件
python clean_output.py clean --days 7 --confirm

# 删除更久之前的文件
python clean_output.py clean --days 30 --confirm
```

### 自定义输出目录
```bash
# 指定自定义输出目录
python clean_output.py --output-dir my_output list
python clean_output.py --output-dir my_output clean --days 7
```

## 🎯 最佳实践总结

1. **首次使用**: 运行 `python demo.py --demo` 了解功能
2. **参数调整**: 根据需求调整爬取深度和数量
3. **文件管理**: 定期使用清理工具管理输出文件
4. **可视化**: 利用生成的图表分析引用关系
5. **数据分析**: 使用JSON数据进行进一步研究

## 🎉 恭喜！

你现在拥有了一个功能强大的学术引用爬虫工具。这个系统可以帮助你：

- 📚 **学术研究**: 快速了解某个领域的研究脉络
- 🔍 **文献调研**: 发现相关论文和研究方向
- 📊 **影响力分析**: 分析学术影响力和引用模式
- 🌐 **网络分析**: 构建学术合作和引用网络

开始你的学术探索之旅吧！🚀
