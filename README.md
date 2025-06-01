# 🕷️ PaperTracer

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PaperTracer 是一个强大的Google Scholar引用关系爬虫工具，可以递归爬取学术论文的引用网络并构建树形数据结构。

## ✨ 功能特性

- 🔍 **智能解析**: 自动解析论文标题、作者、年份、引用次数等信息
- 🌳 **树形结构**: 构建清晰的引用关系树，支持多层递归
- 💾 **数据导出**: 支持JSON格式导出，便于后续分析
- 🌐 **交互式可视化**: 生成交互式HTML页面，支持鼠标悬停、点击访问等功能
- 📊 **多种可视化**: 支持静态图表和动态HTML两种可视化方式
- 🛡️ **反爬保护**: 内置随机延迟和User-Agent轮换机制
- ⚙️ **灵活配置**: 可自定义爬取深度、每层论文数量等参数
- 📈 **详细统计**: 提供爬取结果的详细统计信息

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行演示

```bash
# 运行完整演示（推荐首次使用）
python demo.py

# 查看帮助信息
python demo.py --help

# 使用不同配置
python demo.py --config production --depth 3
python demo.py --config quick --no-visualization
```

### 3. 基本使用

```python
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json

# 创建爬虫实例
crawler = GoogleScholarCrawler(
    max_depth=3,              # 最大递归深度
    max_papers_per_level=10,  # 每层最多爬取论文数
    delay_range=(1, 3)        # 请求间隔时间范围（秒）
)

# 设置起始URL（Google Scholar的引用页面）
start_url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"

# 构建引用树
citation_tree = crawler.build_citation_tree(start_url)

if citation_tree:
    # 打印树结构
    print_citation_tree(citation_tree)
    
    # 保存为JSON文件（会自动保存到output/目录）
    save_tree_to_json(citation_tree, "output/citation_tree.json")
```

### 3. 使用测试工具

```bash
# 运行基本功能测试
python test_crawler.py --test

# 交互式配置和测试
python test_crawler.py --interactive

# 显示帮助信息
python test_crawler.py
```

## 📊 数据结构

### Paper 类
```python
@dataclass
class Paper:
    title: str           # 论文标题
    authors: str         # 作者信息
    year: str           # 发表年份
    citation_count: int  # 引用次数
    url: str            # 论文链接
    cited_by_url: str   # 被引用页面链接
    abstract: str       # 摘要
```

### CitationNode 类
```python
@dataclass 
class CitationNode:
    paper: Paper                    # 论文信息
    children: List['CitationNode']  # 子节点列表
    depth: int                     # 节点深度
```

## ⚙️ 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| max_depth | int | 3 | 最大递归深度 |
| max_papers_per_level | int | 10 | 每层最多爬取的论文数量 |
| delay_range | tuple | (1, 3) | 请求间隔时间范围（秒） |

## 📁 输出文件

### 目录结构
所有输出文件都会保存在 `output/` 目录中，按时间戳命名以避免覆盖：

```
output/
├── demo_20250601_143052_citation_tree.json    # 引用数据文件
├── demo_20250601_143052_simple.png            # 简单网络图
├── demo_20250601_143052_stats.png             # 统计图表
└── README.md                                   # 输出目录说明
```

### JSON格式
生成的JSON文件包含完整的树形结构：

```json
{
  "paper": {
    "title": "论文标题",
    "authors": "作者信息",
    "year": "2024",
    "citation_count": 50,
    "url": "论文链接",
    "cited_by_url": "被引用页面链接",
    "abstract": "摘要信息"
  },
  "depth": 0,
  "children": [
    {
      "paper": { ... },
      "depth": 1,
      "children": [ ... ]
    }
  ]
}
```

### 可视化图表
- **简单网络图** (`*_simple.png`): 显示引用关系的网络结构
- **统计图表** (`*_stats.png`): 包含深度分布、引用次数分布等统计信息

## 🔧 高级用法

### 自定义爬虫配置

```python
# 创建自定义配置的爬虫
crawler = GoogleScholarCrawler(
    max_depth=5,               # 更深的递归
    max_papers_per_level=20,   # 更多论文
    delay_range=(2, 5)         # 更长的延迟
)

# 设置自定义User-Agent
crawler.session.headers.update({
    'User-Agent': 'Your Custom User Agent'
})
```

### 批量处理多个链接

```python
urls = [
    "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en",
    "https://scholar.google.com/scholar?cites=另一个ID&as_sdt=2005&sciodt=0,5&hl=en"
]

for i, url in enumerate(urls):
    tree = crawler.build_citation_tree(url)
    if tree:
        save_tree_to_json(tree, f"output/citation_tree_{i}.json")
```

### 可视化工具

```bash
# 创建所有类型的可视化图表
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --type all

# 只创建简单网络图
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --type simple

# 指定输出路径
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --output output/my_visualization
```

### 交互式HTML可视化

```bash
# 创建交互式HTML可视化
python html_visualizer.py output/demo_20250601_143052_citation_tree.json --output output/interactive.html

# 使用浏览器打开生成的HTML文件
open output/interactive.html  # macOS
# 或
start output/interactive.html  # Windows
# 或
xdg-open output/interactive.html  # Linux
```

**HTML可视化功能特性:**
- 🖱️ 鼠标悬停显示论文详细信息（标题、作者、年份、引用次数、摘要）
- 🔗 点击节点访问论文原始链接
- 🎛️ 支持树形和力导向两种布局模式
- 🔍 支持缩放和拖拽操作
- 📊 显示实时统计信息和深度图例
- 🎨 美观的现代化界面设计
- 📱 响应式布局，支持不同屏幕尺寸

## ⚠️ 注意事项

1. **合规使用**: 请遵守Google Scholar的使用条款和robots.txt
2. **请求频率**: 避免过于频繁的请求，建议设置合适的延迟时间
3. **数据量控制**: 大规模爬取可能需要很长时间，建议合理设置深度和数量限制
4. **网络稳定性**: 确保网络连接稳定，爬虫会自动处理一些网络错误
5. **反爬机制**: 如遇到访问限制，可尝试增加延迟时间或更换User-Agent

## 🐛 常见问题

### Q: 爬虫返回空结果？
A: 可能原因：
- URL格式不正确
- 网络连接问题
- Google Scholar临时限制访问
- 论文没有被引用记录

### Q: 如何获取Google Scholar的引用链接？
A: 
1. 在Google Scholar中搜索目标论文
2. 点击论文下方的"Cited by X"链接
3. 复制浏览器地址栏中的URL

### Q: 爬取速度太慢？
A: 可以尝试：
- 减少`delay_range`的值（但要注意反爬风险）
- 减少`max_papers_per_level`
- 减少`max_depth`

## 📈 性能建议

- **小规模测试**: 首次使用建议设置`max_depth=2`, `max_papers_per_level=5`
- **中等规模**: `max_depth=3`, `max_papers_per_level=10`
- **大规模爬取**: 分批处理，设置较长的延迟时间

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 📄 许可证

本项目仅供学术研究和个人学习使用，请勿用于商业用途。
