# 🕷️ PaperTracer - 功能特性与更新日志

## 📋 项目概述

PaperTracer 是一个强大的Google Scholar引用网络爬虫，能够递归爬取学术论文引用关系并构建树状数据结构。

## ✨ 核心功能

- 🔍 **智能解析**: 自动解析论文标题、作者、年份、引用次数等信息
- 🌳 **树状结构**: 构建清晰的引用关系树，支持多层级递归
- 💾 **数据导出**: 支持JSON格式导出，便于后续分析
- 🌐 **交互式可视化**: 生成交互式HTML页面，支持鼠标悬停、点击访问等
- 📊 **多种可视化**: 支持静态图表和动态HTML可视化
- 🛡️ **反爬虫保护**: 内置随机延迟和User-Agent轮换机制
- ⚙️ **灵活配置**: 可自定义爬取深度、每层论文数量等
- 📈 **详细统计**: 提供爬取结果的详细统计信息

## 🚀 增强功能 (v2.0+)

### 1. 智能429错误处理
- **指数退避策略**: 最大延迟60秒，支持手动CAPTCHA处理
- **时间窗口错误追踪**: 1分钟窗口内的错误统计
- **自适应延迟调整**: 根据错误历史动态调整策略
- **成功请求重置**: 成功请求后自动重置错误计数

**核心方法**:
- `_handle_429_error()`: 专门处理429错误
- `_reset_429_tracking()`: 重置错误追踪状态
- `_adaptive_delay()`: 自适应延迟策略

### 2. 会话持久化和恢复
- **会话状态管理**: 跟踪session_id、last_429_time、consecutive_429_count
- **自动保存/加载**: `save_session_state()`和`load_session_state()`方法
- **爬取过程自动保存**: 爬取操作期间自动保存会话状态

### 3. 增强版演示脚本 (`enhanced_demo.py`)
- **会话恢复**: `--resume`选项支持恢复中断的会话
- **自动保存**: 可配置间隔的自动会话状态保存
- **激进延迟策略**: `--aggressive-delays`选项
- **增强命令行界面**: 完整的会话管理选项

### 4. 会话管理工具 (`session_manager.py`)
- **会话列表**: 显示所有可用会话的详细信息
- **统计分析**: 分析会话统计数据和性能指标
- **清理功能**: 可配置保留期的旧会话清理
- **数据导出**: 支持JSON、CSV、TXT格式导出
- **会话合并**: 将多个会话合并为组合数据集

### 5. 性能监控系统 (`performance_monitor.py`)
- **实时监控面板**: 显示系统指标的实时性能面板
- **网络延迟测量**: 网络延迟测量和趋势分析
- **优化建议**: 基于性能模式的优化建议
- **性能报告**: 性能报告生成和历史跟踪

### 6. 手动CAPTCHA处理
- **浏览器自动切换**: 自动切换到有头浏览器模式
- **用户友好界面**: 打开浏览器窗口供用户手动处理
- **清晰操作指导**: 提供详细的操作说明
- **重试和错误恢复**: 支持多次重试和错误恢复机制

### 7. Chrome驱动兼容性
- **兼容性fallback**: 处理新版本Chrome的选项不兼容问题
- **自动降级**: 当excludeSwitches选项失效时自动使用替代方法

## 📊 交互式HTML可视化

### 🖱️ 交互式操作
- **鼠标悬停**: 显示论文详细信息（标题、作者、年份、引用次数、摘要）
- **点击节点**: 直接访问论文的原始链接或Google Scholar页面
- **缩放和拖拽**: 支持鼠标滚轮缩放和拖拽移动画布

### 🎛️ 多种布局模式
- **树形布局**: 层次化显示引用关系，适合查看论文的层级结构
- **力导向布局**: 基于物理模拟的布局，支持拖拽节点调整位置

### 📊 丰富的信息展示
- **深度图例**: 不同颜色标识不同深度的论文
- **统计信息**: 实时显示总论文数、总引用数、最大深度、平均引用等
- **节点大小**: 根据引用次数动态调整节点大小

## 🔧 延迟策略优化

为支持手动CAPTCHA处理，已完成以下优化：

- **最大延迟时间**: 从300秒降低到60秒
- **429错误监控窗口**: 从5分钟缩短到1分钟
- **退避策略**: 使用改进的退避公式 `min(5 * (1.5^n), 60)`

## 🐛 已解决的问题

### Chrome驱动兼容性
- **问题**: `excludeSwitches` Chrome选项在新版本中不兼容
- **解决方案**: 添加兼容性fallback，使用替代的--disable-automation参数

### 429错误自动检测
- 增强页面内容检测，识别包含'429'、'too many requests'、'unusual traffic'等关键词的错误页面
- 自动切换到手动处理模式

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 基础使用
```bash
# 基础爬取
python enhanced_demo.py

# 增强版演示（推荐）
python enhanced_demo.py --config quick --save-session

# 手动CAPTCHA处理
python enhanced_demo.py --manual-captcha --depth 2 --max-papers 5
```

### 3. 会话管理
```bash
# 查看所有会话
python session_manager.py list

# 会话统计分析
python session_manager.py analyze

# 清理旧会话
python session_manager.py cleanup --days 30
```

### 4. 性能监控
```bash
# 启动性能监控
python performance_monitor.py
```

## 📁 项目文件结构

### 核心文件
- `papertracer.py`: 主要爬虫引擎
- `enhanced_demo.py`: 主演示脚本（包含所有功能演示）

### 工具和配置
- `session_manager.py`: 会话管理工具
- `performance_monitor.py`: 性能监控系统
- `html_visualizer.py`: HTML可视化生成器
- `papertracer_config.py`: 配置文件
- `logger.py`: 日志系统

### 数据和输出
- `output/`: 爬取结果输出目录
- `sessions/`: 会话数据存储目录
- `requirements.txt`: 项目依赖

## 📄 许可证

MIT License - 详见 LICENSE 文件
