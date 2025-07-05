# FastChat 投票分析 Web 展示指南

## 概述

本指南介绍如何使用 FastChat 的投票分析工具，包括自定义脚本和官方工具，以及如何通过 Web 界面展示分析结果。

## 方案选择

### 方案一：自定义脚本 (推荐用于快速展示)

使用我们创建的自定义脚本，提供简洁的 Web 界面和自动化分析流程。

### 方案二：官方工具 (推荐用于专业分析)

使用 FastChat 官方的监控和分析工具，提供更全面的功能和专业级的可视化。

## 方案一：自定义脚本使用

### 1. 快速启动

```bash
# 分析数据并启动Web服务器
python auto_analysis.py --log-file 2025-06-26-conv.json

# 只分析数据，不启动Web服务器
python auto_analysis.py --log-file 2025-06-26-conv.json --no-web

# 指定端口
python auto_analysis.py --log-file 2025-06-26-conv.json --port 9000
```

### 2. 功能特点

- ✅ 自动分析投票数据
- ✅ 生成 ELO 排名
- ✅ 创建美观的 Web 界面
- ✅ 实时数据更新
- ✅ 响应式设计，支持移动端
- ✅ 交互式图表

### 3. 生成的文件

- `vote_analysis.csv` - 投票统计数据
- `elo_rankings.csv` - ELO 排名数据
- `web_dashboard.html` - Web 展示页面

### 4. Web 界面功能

- 📊 **统计概览**: 总投票数、对战数、模型数、时间跨度
- 🥧 **投票类型分布**: 左方获胜、右方获胜、平局的饼图
- 📈 **模型胜率对比**: 各模型胜率的柱状图
- 🏅 **ELO 排名表**: 详细的 ELO 评分和排名
- 📋 **详细统计表**: 完整的模型表现统计

## 方案二：官方工具使用

### 1. 快速启动

```bash
# 使用官方工具进行完整分析
python official_analysis.py --log-file 2025-06-26-conv.json

# 只分析数据，不启动Web服务器
python official_analysis.py --log-file 2025-06-26-conv.json --no-web

# 跳过数据清理步骤
python official_analysis.py --log-file 2025-06-26-conv.json --skip-clean
```

### 2. 官方工具功能

- 🧹 **数据清理**: `clean_battle_data.py`
- 📊 **ELO 分析**: `elo_analysis.py`
- 📈 **基础统计**: `basic_stats.py`
- 🌐 **Web 监控**: `monitor.py`

### 3. 生成的文件

- `clean_battle_YYYYMMDD.json` - 清理后的对战数据
- `elo_results_YYYYMMDD.json` - ELO 分析结果
- `analysis_report.md` - 分析报告

### 4. 官方 Web 界面功能

- 🏆 **排行榜**: 完整的模型排行榜
- 📊 **统计图表**: 多种可视化图表
- 🔍 **实时监控**: 实时数据更新
- 📱 **分类分析**: 按类别分析模型表现
- 🎯 **置信区间**: 统计置信区间分析

## 手动使用官方工具

### 1. 数据清理

```bash
# 简单模式
python -m fastchat.serve.monitor.clean_battle_data --mode simple

# 对话发布模式
python -m fastchat.serve.monitor.clean_battle_data --mode conv_release

# 排除特定模型
python -m fastchat.serve.monitor.clean_battle_data --exclude-model-names model1 model2

# 限制文件数量
python -m fastchat.serve.monitor.clean_battle_data --max-num-files 10
```

### 2. ELO 分析

```bash
# 使用清理后的数据进行分析
python -m fastchat.serve.monitor.elo_analysis --input-file clean_battle_20250626.json

# 指定输出文件
python -m fastchat.serve.monitor.elo_analysis --input-file clean_battle_20250626.json --output-file elo_results.json
```

### 3. 基础统计

```bash
# 生成基础统计报告
python -m fastchat.serve.monitor.basic_stats

# 限制文件数量
python -m fastchat.serve.monitor.basic_stats --max-num-files 10
```

### 4. Web 监控界面

```bash
# 启动监控界面
python -m fastchat.serve.monitor.monitor --port 8080

# 指定 ELO 结果文件
python -m fastchat.serve.monitor.monitor --elo-results-file elo_results.json --port 8080
```

## 数据格式说明

### 投票日志格式

```json
{
  "tstamp": 1750938195.5373,
  "type": "leftvote",
  "models": ["HKGAI-V1", "HKGAI-V1-Thinking"],
  "states": [...],
  "ip": "127.0.0.1"
}
```

### 投票类型

- `leftvote`: 左方模型获胜
- `rightvote`: 右方模型获胜
- `tievote`: 平局
- `bothbad_vote`: 双方都不好

## 常见问题

### Q: 如何查看实时投票数据？

A: 使用官方监控工具：
```bash
python -m fastchat.serve.monitor.monitor --port 8080
```

### Q: 如何分析特定时间段的投票？

A: 可以过滤日志文件或使用官方工具的日期过滤功能。

### Q: 如何比较多个模型的表现？

A: ELO 分析会自动计算所有模型之间的对战结果和排名。

### Q: Web 界面无法访问？

A: 检查端口是否被占用，尝试使用其他端口：
```bash
python auto_analysis.py --log-file data.json --port 9000
```

### Q: 数据更新后如何刷新？

A: 
- 自定义脚本：页面会自动每30秒刷新一次
- 官方工具：重新运行分析脚本

## 高级用法

### 1. 批量分析多个日志文件

```bash
# 合并多个日志文件
cat log1.json log2.json log3.json > combined_log.json

# 分析合并后的文件
python auto_analysis.py --log-file combined_log.json
```

### 2. 自定义 ELO 参数

修改 `elo_analysis_simple.py` 中的 K 因子：
```python
K_FACTOR = 32  # 可以调整为 16, 24, 32 等
```

### 3. 导出分析结果

```bash
# 导出 CSV 格式
python vote_analysis.py --log-file data.json --export
python elo_analysis_simple.py --log-file data.json --export

# 导出 JSON 格式 (官方工具)
python -m fastchat.serve.monitor.elo_analysis --input-file clean_data.json --output-file results.json
```

## 性能优化

### 1. 大文件处理

对于大型日志文件，建议：
- 使用官方工具的数据清理功能
- 分批处理数据
- 使用 `--max-num-files` 参数限制处理文件数量

### 2. 内存优化

- 定期清理临时文件
- 使用流式处理大文件
- 避免同时加载过多数据到内存

## 故障排除

### 1. 依赖问题

确保安装了所有必要的包：
```bash
pip install pandas numpy matplotlib plotly gradio
```

### 2. 权限问题

确保有读写文件的权限：
```bash
chmod +x auto_analysis.py
chmod +x official_analysis.py
```

### 3. 端口冲突

如果端口被占用，使用其他端口：
```bash
python auto_analysis.py --log-file data.json --port 9000
```

## 总结

- **快速展示**: 使用 `auto_analysis.py`
- **专业分析**: 使用 `official_analysis.py`
- **实时监控**: 使用官方 `monitor.py`
- **数据导出**: 使用 `--export` 参数

选择适合你需求的方案，开始分析你的 FastChat 投票数据吧！ 