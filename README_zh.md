[← 返回语言选择](README.md)
# 🕷️ PaperTracer

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PaperTracer 是一个强大的 Google Scholar 引用爬虫，能够递归地爬取学术论文引用网络并构建树状数据结构。

## ✨ 功能特点

- 🔍 **智能解析**：自动解析论文标题、作者、年份、引用次数等信息
- 🌳 **树状结构**：构建清晰的引用关系树，支持多级递归
- 💾 **数据导出**：支持JSON格式导出，方便进一步分析
- 🌐 **交互式可视化**：生成支持鼠标悬停、点击访问等操作的交互式HTML页面
- 📊 **多种可视化方式**：支持静态图表和动态HTML可视化
- 🛡️ **反爬虫保护**：内置随机延迟和User-Agent轮换机制
- ⚙️ **灵活配置**：可自定义爬取深度、每层论文数量等参数
- 📈 **详细统计**：提供爬取结果的详细统计数据

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行演示

```bash
# 运行完整演示（推荐首次使用）
python enhanced_demo.py

# 查看帮助信息
python enhanced_demo.py --help

# 使用不同配置
python enhanced_demo.py --config production --depth 3
python enhanced_demo.py --config quick --no-visualization

# 手动CAPTCHA模式
python enhanced_demo.py --manual-captcha --depth 2 --max-papers 5
```

### 3. 基本用法

```python
from papertracer import GoogleScholarCrawler, print_citation_tree, save_tree_to_json

# 创建爬虫实例
crawler = GoogleScholarCrawler(
    max_depth=3,              # 最大递归深度
    max_papers_per_level=10,  # 每层最大论文数
    delay_range=(1, 3)        # 请求延迟范围（秒）
)

# 设置起始URL（Google Scholar引用页面）
start_url = "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en"

# 构建引用树
citation_tree = crawler.build_citation_tree(start_url)

if citation_tree:
    # 打印树状结构
    print_citation_tree(citation_tree)
    
    # 保存为JSON文件（自动保存到output/目录）
    save_tree_to_json(citation_tree, "output/citation_tree.json")
```

### 4. 使用测试工具

```bash
# 运行基本功能测试
python test_crawler.py --test

# 交互式配置和测试
python test_crawler.py --interactive

# 显示帮助信息
python test_crawler.py
```

## 📊 数据结构

### Paper类
```python
@dataclass
class Paper:
    title: str           # 论文标题
    authors: str         # 作者信息
    year: str            # 发表年份
    citation_count: int  # 引用次数
    url: str             # 论文URL
    cited_by_url: str    # 引用页面URL
    abstract: str        # 摘要
```

### CitationNode类
```python
@dataclass 
class CitationNode:
    paper: Paper                    # 论文信息
    children: List['CitationNode']  # 子节点列表
    depth: int                      # 节点深度
```

## ⚙️ 配置参数

| 参数 | 类型 | 默认值 | 描述 |
|----------|------|---------|-------------|
| max_depth | int | 3 | 最大递归深度 |
| max_papers_per_level | int | 10 | 每层最大爬取论文数 |
| delay_range | tuple | (1, 3) | 请求延迟范围（秒） |

## 📁 输出文件

### 目录结构
所有输出文件保存在`output/`目录下，并带有时间戳防止覆盖：
```
output/
├── demo_20250601_143052_citation_tree.json    # 引用数据文件
├── demo_20250601_143052_simple.png            # 简单网络图
├── demo_20250601_143052_stats.png             # 统计图表
└── README.md                                  # 输出目录说明
```

### JSON格式
生成的JSON文件包含完整的树状结构：
```json
{
  "paper": {
    "title": "论文标题",
    "authors": "作者信息",
    "year": "2024",
    "citation_count": 50,
    "url": "论文URL",
    "cited_by_url": "引用页面URL",
    "abstract": "摘要"
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
- **简单网络图** (`*_simple.png`)：展示引用关系网络
- **统计图表** (`*_stats.png`)：包含深度分布、引用次数分布等

## 🔧 高级用法

### 自定义爬虫配置
```python
# 创建自定义爬虫
crawler = GoogleScholarCrawler(
    max_depth=5,               # 更深递归
    max_papers_per_level=20,   # 更多论文
    delay_range=(2, 5)         # 更长延迟
)

# 设置自定义User-Agent
crawler.session.headers.update({
    'User-Agent': '您的自定义User-Agent'
})
```

### 批量处理多个链接
```python
urls = [
    "https://scholar.google.com/scholar?cites=11002616430871081935&as_sdt=2005&sciodt=0,5&hl=en",
    "https://scholar.google.com/scholar?cites=ANOTHER_ID&as_sdt=2005&sciodt=0,5&hl=en"
]

for i, url in enumerate(urls):
    tree = crawler.build_citation_tree(url)
    if tree:
        save_tree_to_json(tree, f"output/citation_tree_{i}.json")
```

### 可视化工具
```bash
# 创建所有可视化类型
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --type all

# 仅创建简单网络图
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --type simple

# 指定输出路径
python visualize_tree.py output/demo_20250601_143052_citation_tree.json --output output/my_visualization
```

### 交互式HTML可视化
```bash
# 创建交互式HTML可视化
python html_visualizer.py output/demo_20250601_143052_citation_tree.json --output output/interactive.html

# 在浏览器中打开生成的HTML文件
open output/interactive.html  # macOS
# 或
start output/interactive.html  # Windows
# 或
xdg-open output/interactive.html  # Linux
```

**HTML可视化功能：**
- 🖱️ 鼠标悬停显示论文详情（标题、作者、年份、引用次数、摘要）
- 🔗 点击节点访问原始论文链接
- 🎛️ 支持树状和力导向布局
- 🔍 支持缩放和拖拽操作
- 📊 显示实时统计数据和深度图例
- 🎨 现代UI设计
- 📱 响应式布局，适配不同屏幕尺寸

## ⚠️ 重要注意事项

1. **合规性**：请遵守Google Scholar的使用条款和robots.txt
2. **请求频率**：避免过多请求，设置适当延迟
3. **数据量控制**：大规模爬取可能需要较长时间
4. **网络稳定性**：确保网络连接稳定
5. **反爬机制**：如遇访问限制，请增加延迟或更换User-Agent

## 🐛 常见问题

### Q: 爬虫返回空结果？
A: 可能原因：
- URL格式不正确
- 网络连接问题
- Google Scholar临时访问限制
- 论文无引用记录

### Q: 如何获取Google Scholar引用链接？
A: 
1. 在Google Scholar中搜索目标论文
2. 点击论文下方的"被引用次数"链接
3. 从浏览器地址栏复制URL

### Q: 爬取速度太慢？
A: 尝试：
- 减小`delay_range`值（但需注意反爬机制）
- 减小`max_papers_per_level`
- 减小`max_depth`

## 📈 性能建议

- **小规模测试**：首次使用时，设置`max_depth=2`, `max_papers_per_level=5`
- **中等规模**：`max_depth=3`, `max_papers_per_level=10`
- **大规模爬取**：分批次处理，使用更长延迟

## 🤝 贡献

欢迎提交Issues和Pull Requests来改进本项目！

## 📄 许可

本项目仅供学术研究和个人学习使用，禁止商业用途。
