# FastChat 一键报告生成脚本使用指南

## 概述

`generate_report.py` 是一个自动化脚本，可以一键分析 FastChat Arena 投票数据并生成美观的报告，支持定时任务执行。

## 功能特性

- 🚀 **一键生成**: 自动查找最新日志文件并分析
- 📊 **多格式报告**: 生成HTML可视化报告和Markdown摘要
- 🎨 **美观界面**: 现代化的响应式设计，支持图表和表格
- 🧹 **自动清理**: 可配置的旧报告清理功能
- ⏰ **定时任务**: 支持crontab等定时任务系统
- 📁 **灵活配置**: 支持自定义输出目录和文件模式

## 快速开始

### 1. 基本使用

```bash
# 使用默认设置（自动查找最新日志文件）
python generate_report.py

# 指定日志文件
python generate_report.py --log-file 2025-06-26-conv.json

# 指定日志目录
python generate_report.py --log-dir /path/to/logs
```

### 2. 自定义输出

```bash
# 指定输出目录
python generate_report.py --output-dir /path/to/reports

# 只生成HTML报告
python generate_report.py --html-only

# 只生成摘要报告
python generate_report.py --summary-only
```

### 3. 清理设置

```bash
# 清理7天前的旧报告（默认）
python generate_report.py --cleanup-days 7

# 不清理旧报告
python generate_report.py --no-cleanup

# 清理30天前的旧报告
python generate_report.py --cleanup-days 30
```

## 命令行参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--log-file` | str | None | 指定日志文件路径 |
| `--log-dir` | str | "." | 日志文件目录 |
| `--pattern` | str | "*-conv.json" | 日志文件匹配模式 |
| `--output-dir` | str | "reports" | 报告输出目录 |
| `--cleanup-days` | int | 7 | 清理N天前的旧报告 |
| `--no-cleanup` | flag | False | 不清理旧报告 |
| `--html-only` | flag | False | 只生成HTML报告 |
| `--summary-only` | flag | False | 只生成摘要报告 |

## 输出文件

脚本会在指定的输出目录中生成以下文件：

### HTML报告
- `report_YYYYMMDD_HHMMSS.html` - 完整的可视化报告
- 包含图表、表格、统计信息
- 响应式设计，支持移动设备

### 摘要报告
- `summary_YYYYMMDD_HHMMSS.md` - Markdown格式摘要
- 包含关键统计数据和排名信息
- 适合邮件发送或文档存档

### 数据文件
- `vote_analysis.csv` - 投票统计分析
- `elo_rankings.csv` - ELO排名数据
- `vote_distribution.json` - 投票分布数据

## 定时任务配置

### 1. 每小时运行

```bash
# 编辑crontab
crontab -e

# 添加以下行（每小时运行）
0 * * * * cd /path/to/FastChat && /path/to/python generate_report.py --output-dir /path/to/reports
```

### 2. 每天运行

```bash
# 每天凌晨2点运行
0 2 * * * cd /path/to/FastChat && /path/to/python generate_report.py --output-dir /path/to/reports
```

### 3. 每周运行

```bash
# 每周日凌晨3点运行
0 3 * * 0 cd /path/to/FastChat && /path/to/python generate_report.py --output-dir /path/to/reports --cleanup-days 30
```

## 使用示例

### 示例1: 基本分析

```bash
# 分析最新日志文件
python generate_report.py

# 输出示例:
# 🚀 FastChat 一键报告生成脚本
# ==================================================
# 📄 使用日志文件: 2025-06-26-conv.json
# 🔄 投票统计分析...
# ✅ 投票统计分析 完成
# 🔄 ELO排名分析...
# ✅ ELO排名分析 完成
# 🌐 创建报告HTML页面...
# ✅ 报告已生成: report_20250626_143022.html
# 📋 创建摘要报告...
# ✅ 摘要报告已生成: summary_20250626_143022.md
# 🧹 清理7天前的旧报告...
# ==================================================
# ✅ 报告生成完成！
# 📁 输出目录: /path/to/reports
# 📊 生成的文件:
#   - report_20250626_143022.html
#   - summary_20250626_143022.md
```

### 示例2: 自定义配置

```bash
# 指定日志文件和输出目录
python generate_report.py \
  --log-file /path/to/logs/2025-06-26-conv.json \
  --output-dir /var/www/reports \
  --cleanup-days 14 \
  --html-only

# 输出示例:
# 🚀 FastChat 一键报告生成脚本
# ==================================================
# 📄 使用日志文件: /path/to/logs/2025-06-26-conv.json
# 🔄 投票统计分析...
# ✅ 投票统计分析 完成
# 🔄 ELO排名分析...
# ✅ ELO排名分析 完成
# 🌐 创建报告HTML页面...
# ✅ 报告已生成: report_20250626_143022.html
# 🧹 清理14天前的旧报告...
# ==================================================
# ✅ 报告生成完成！
# 📁 输出目录: /var/www/reports
# 📊 生成的文件:
#   - report_20250626_143022.html
```

## 报告内容

### HTML报告包含

1. **统计概览**
   - 总投票数
   - 参与模型数
   - 有效对战数
   - 分析日期

2. **可视化图表**
   - 投票类型分布（饼图）
   - 模型胜率对比（柱状图）

3. **ELO排名表**
   - 排名、模型名称、ELO评分
   - 总对战、胜利、失败、平局、胜率

4. **详细统计表**
   - 各模型的详细统计数据
   - 胜率、平局率、失败率

### 摘要报告包含

1. **报告信息**
   - 生成时间、分析工具、数据来源

2. **统计概览**
   - 关键统计数据

3. **投票分布**
   - 左方获胜、右方获胜、平局次数

4. **ELO排名结果**
   - 每个模型的详细排名信息

5. **详细统计表格**
   - Markdown格式的统计表格

## 故障排除

### 常见问题

1. **找不到日志文件**
   ```bash
   # 检查日志文件是否存在
   ls -la *.json
   
   # 指定正确的日志文件
   python generate_report.py --log-file your-log-file.json
   ```

2. **权限问题**
   ```bash
   # 确保脚本有执行权限
   chmod +x generate_report.py
   
   # 确保输出目录可写
   mkdir -p reports && chmod 755 reports
   ```

3. **依赖问题**
   ```bash
   # 确保安装了必要的依赖
   pip install pandas numpy matplotlib
   ```

### 日志文件格式

脚本期望的日志文件格式：
```json
[
  {
    "tstamp": "2025-06-26 14:30:22",
    "type": "vote",
    "models": ["model1", "model2"],
    "winner": "model1",
    "anony": false,
    "ip": "127.0.0.1"
  }
]
```

## 高级配置

### 环境变量

可以设置以下环境变量来自定义行为：

```bash
# 设置默认输出目录
export FASTCHAT_REPORT_DIR="/var/www/reports"

# 设置日志目录
export FASTCHAT_LOG_DIR="/var/log/fastchat"

# 设置清理天数
export FASTCHAT_CLEANUP_DAYS=7
```

### 配置文件

可以创建配置文件来自定义设置：

```bash
# 创建配置文件
cat > report_config.json << EOF
{
  "default_output_dir": "/var/www/reports",
  "default_log_dir": "/var/log/fastchat",
  "cleanup_days": 7,
  "log_pattern": "*-conv.json"
}
EOF
```

## 性能优化

### 大文件处理

对于大型日志文件，可以考虑：

1. **分批处理**
   ```bash
   # 按日期分割日志文件
   python generate_report.py --log-file 2025-06-26-conv.json
   ```

2. **增量分析**
   ```bash
   # 只分析新增的投票数据
   python generate_report.py --pattern "*-conv-*.json"
   ```

### 内存优化

对于内存受限的环境：

```bash
# 只生成摘要报告（内存占用更少）
python generate_report.py --summary-only

# 清理旧报告释放空间
python generate_report.py --cleanup-days 1
```

## 集成建议

### Web服务器集成

```bash
# 将报告目录配置为Web服务器根目录
sudo ln -s /path/to/reports /var/www/html/fastchat-reports

# 访问报告
# http://your-server/fastchat-reports/
```

### 邮件通知

```bash
# 创建邮件通知脚本
cat > notify_report.sh << 'EOF'
#!/bin/bash
REPORT_DIR="/path/to/reports"
LATEST_REPORT=$(ls -t $REPORT_DIR/report_*.html | head -1)

if [ -n "$LATEST_REPORT" ]; then
    echo "FastChat报告已生成: $LATEST_REPORT" | mail -s "FastChat报告更新" your-email@example.com
fi
EOF

# 在crontab中添加邮件通知
0 2 * * * /path/to/notify_report.sh
```

### 监控集成

```bash
# 检查报告生成状态
python generate_report.py --output-dir /path/to/reports
if [ $? -eq 0 ]; then
    echo "报告生成成功"
else
    echo "报告生成失败"
    # 发送告警
fi
```

## 总结

`generate_report.py` 脚本提供了一个完整的解决方案来自动化 FastChat Arena 投票数据的分析和报告生成。通过合理配置定时任务，可以实现持续的数据监控和报告更新，为模型性能评估提供及时、准确的数据支持。 