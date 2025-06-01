# PaperTracer v2.0 - 使用指南

## 🚀 新增功能 (v2.0)

### 增强演示脚本
使用新的 `demo_enhanced.py` 获得更丰富的功能：

```bash
# 基本使用
python demo_enhanced.py

# 使用生产配置
python demo_enhanced.py --config production --depth 3

# 快速测试
python demo_enhanced.py --config quick --no-visualization

# 自定义URL和输出前缀
python demo_enhanced.py --url "你的URL" --output-prefix "my_analysis"

# 详细输出
python demo_enhanced.py --verbose
```

### 配置管理
新增 `config.py` 提供统一的配置管理：

- **demo**: 快速演示配置 (深度2，每层3篇论文)
- **production**: 生产配置 (深度3，每层5篇论文)  
- **quick**: 快速测试配置 (深度1，每层2篇论文)

### 日志系统
自动生成详细的日志文件：

- 控制台显示重要信息
- 文件记录详细调试信息
- 日志文件保存在 `output/` 目录

### 性能监控
自动监控和报告：

- 内存使用情况
- 网络请求统计
- 处理时间分析
- 性能报告保存

## 📁 输出文件组织

所有文件按时间戳自动命名和组织：

```
output/
├── demo_20250601_143022_citation_tree.json    # 引用数据
├── demo_20250601_143022_simple.png            # 网络图
├── demo_20250601_143022_stats.png             # 统计图
├── papertracer_20250601_143022_log.log        # 日志文件
└── performance_20250601_143022_report.json    # 性能报告
```

## 🛠️ 文件管理

### 查看输出文件
```bash
python clean_output.py list
```

### 清理旧文件
```bash
# 清理7天前的文件
python clean_output.py clean --days 7

# 清理指定类型文件
python clean_output.py clean --file-type png

# 交互式清理
python clean_output.py clean --interactive
```

## ⚡ 快速开始

1. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

2. **简单演示**：
   ```bash
   python demo_enhanced.py --config quick
   ```

3. **查看结果**：
   ```bash
   python clean_output.py list
   ```

## 🔧 高级配置

### 自定义配置
修改 `config.py` 中的参数或创建新的配置预设：

```python
CUSTOM_CONFIG = {
    'max_depth': 4,
    'max_papers_per_level': 10,
    'delay_range': (3, 5),
    'figsize': (20, 15)
}
```

### 日志级别
```bash
# 调试模式
python demo_enhanced.py --verbose

# 查看日志文件
tail -f output/papertracer_*_log.log
```

### 性能调优
- 增加 `delay_range` 避免被限制
- 调整 `max_papers_per_level` 控制数据量
- 使用 `quick` 配置进行测试

## 📊 输出说明

- **JSON文件**: 结构化的引用关系数据
- **网络图**: 论文引用关系的可视化
- **统计图**: 引用统计和分析图表
- **日志文件**: 详细的运行记录
- **性能报告**: 运行时性能指标

## 🔄 升级说明

从 v1.x 升级到 v2.0：

1. 原有脚本继续可用
2. 建议使用新的 `demo_enhanced.py`
3. 配置参数可通过 `config.py` 统一管理
4. 输出文件自动带时间戳，不会覆盖
