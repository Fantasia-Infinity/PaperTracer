# 429跳过功能文档

# 429跳过功能文档

## 功能概述

新增的`--skip-429`参数允许用户在遇到429错误（Too Many Requests）或CAPTCHA时，执行除浏览器手动处理外的所有自动化策略。这个功能特别适合需要快速爬取、但仍希望尝试自动化解决方案的场景。

### 🔄 智能跳过策略

在`--skip-429`模式下，系统会：

**✅ 仍然执行的策略：**

- 自动重试机制
- 指数退避延迟
- 请求头更新（User-Agent等）
- 短暂延迟后重试
- 基础的反爬虫规避策略

**❌ 跳过的策略：**

- 浏览器窗口弹出
- 手动CAPTCHA处理
- 用户交互干预

## 使用方法

### 命令行参数

在`enhanced_demo.py`中添加`--skip-429`参数：

```bash
# 启用429跳过模式
python enhanced_demo.py --url "your_url" --skip-429

# 结合其他参数使用（极速模式）
python enhanced_demo.py --url "your_url" --skip-429 --no-delays --config demo --depth 3 --max-papers 5
```

### 编程接口

在代码中直接使用：

```python
from papertracer import GoogleScholarCrawler

# 启用429跳过模式
crawler = GoogleScholarCrawler(
    max_depth=3,
    max_papers_per_level=10,
    skip_429_errors=True  # 新增参数
)
```

## 功能特点

### ✅ 优点

1. **极速模式**: 遇到429错误直接跳过，大幅提升爬取速度
2. **无人值守**: 不需要手动干预处理CAPTCHA或429错误
3. **资源节约**: 不消耗额外时间和计算资源尝试修复
4. **简化流程**: 适合快速原型开发和测试

### ⚠️ 注意事项

1. **数据不完整**: 跳过的URL将不会被爬取，可能导致数据缺失
2. **引用链中断**: 如果关键节点被跳过，可能影响引用树的完整性
3. **统计偏差**: 最终统计数据可能不准确
4. **适用场景有限**: 仅适合对数据完整性要求不高的快速测试场景

## 使用场景

### 适合使用

- 快速原型开发和测试
- 大致了解引用网络结构
- 系统性能测试
- 批量处理多个URL时的快速筛选

### 不适合使用

- 学术研究需要完整数据
- 正式的引用分析报告
- 需要精确统计数据的场景
- 重要论文的详细分析

## 工作原理

### 默认模式 (skip_429_errors=False)

```
429错误 → 尝试手动浏览器处理 → 用户干预 → 继续爬取
```

### 跳过模式 (skip_429_errors=True)

```
429错误 → 记录日志 → 直接跳过 → 继续下一个URL
```

## 日志输出

### 跳过模式启用时
```
🚨 检测到429错误 (Too Many Requests)
⏭️  429跳过模式已启用，直接跳过此URL
```

### 配置信息显示
```
   - 429跳过模式: 启用
```

## 配置示例

### 极速爬取配置
```bash
python enhanced_demo.py \
  --url "your_scholar_url" \
  --skip-429 \
  --no-delays \
  --config demo \
  --depth 3 \
  --max-papers 5 \
  --no-browser
```

### 对比测试配置
```bash
# 标准模式
python enhanced_demo.py --url "url" --config demo

# 跳过模式
python enhanced_demo.py --url "url" --config demo --skip-429
```

## 兼容性

- ✅ 与所有现有参数兼容
- ✅ 可与`--no-delays`组合使用
- ✅ 可与`--no-browser`组合使用
- ⚠️ 与`--manual-captcha`功能互斥（跳过模式下不会触发手动处理）

## 更新历史

- **版本**: 2025-06-02
- **新增**: `--skip-429`命令行参数
- **新增**: `skip_429_errors`构造函数参数
- **修改**: `_handle_429_error()`方法支持跳过逻辑
- **更新**: 配置显示和示例命令
