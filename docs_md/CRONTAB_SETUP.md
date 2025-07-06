# FastChat 投票分析报告自动生成设置指南

## 概述

本指南将帮助您设置定时任务，自动生成最新的 FastChat 投票分析报告，确保报告始终包含最新的投票数据。

## 问题解决

### 原始问题
用户报告生成的投票分析报告不包含当天的最新数据。

### 解决方案
1. **自动检测最新日志文件**: 修改了 `generate_report.py` 脚本，使其能够自动找到最新的日志文件
2. **定时任务自动更新**: 提供了定时任务脚本，可以定期自动生成最新报告
3. **实时数据更新**: 确保每次运行都能获取到最新的投票数据

## 快速设置

### 1. 手动运行（立即生成最新报告）

```bash
# 自动检测最新日志文件并生成报告
python generate_report.py

# 或者指定特定的日志文件
python generate_report.py --log-file 2025-07-04-conv.json
```

### 2. 设置定时任务

#### 方法一：使用提供的脚本

```bash
# 给脚本添加执行权限
chmod +x auto_report_schedule.sh

# 测试脚本运行
./auto_report_schedule.sh
```

#### 方法二：直接配置 crontab

```bash
# 编辑 crontab
crontab -e

# 添加以下任务（根据需要选择一个）
```

## 定时任务配置示例

### 每5分钟更新一次（实时监控）
```bash
*/5 * * * * cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
```

### 每15分钟更新一次（推荐）
```bash
*/15 * * * * cd /path/to/FastChat && /path/to/auto_report_schedule.sh
```

### 每30分钟更新一次
```bash
*/30 * * * * cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
```

### 每小时更新一次
```bash
0 * * * * cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
```

### 每天更新一次（凌晨2点）
```bash
0 2 * * * cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
```

## 高级配置

### 1. 带日志记录的定时任务

```bash
# 每15分钟运行，记录日志
*/15 * * * * cd /path/to/FastChat && python generate_report.py >> /var/log/fastchat_report.log 2>&1
```

### 2. 邮件通知

```bash
# 每小时运行，失败时发送邮件
0 * * * * cd /path/to/FastChat && python generate_report.py || echo "FastChat报告生成失败" | mail -s "FastChat Alert" admin@example.com
```

### 3. 多模式定时任务

```bash
# 工作时间每15分钟更新，非工作时间每小时更新
*/15 9-18 * * 1-5 cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
0 * * * 0,6 cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
0 0-8,19-23 * * 1-5 cd /path/to/FastChat && python generate_report.py >/dev/null 2>&1
```

## 验证设置

### 1. 检查 crontab 是否正确设置

```bash
# 查看当前的 crontab 任务
crontab -l
```

### 2. 检查定时任务是否正在运行

```bash
# 查看系统日志
tail -f /var/log/syslog | grep CRON

# 或者在 macOS 上
tail -f /var/log/system.log | grep cron
```

### 3. 手动测试脚本

```bash
# 测试自动报告生成脚本
./auto_report_schedule.sh

# 检查生成的日志
tail -f auto_report.log
```

## 监控和维护

### 1. 检查报告生成状态

```bash
# 查看最近生成的报告
ls -lt reports/ | head -5

# 查看最新报告的内容
cat reports/$(ls -t reports/ | head -1)/summary.md
```

### 2. 监控日志文件

```bash
# 查看自动报告生成日志
tail -f auto_report.log

# 查看 FastChat 系统日志
tail -f *.log
```

### 3. 清理旧报告

```bash
# 手动清理30天前的旧报告
python generate_report.py --cleanup-days 30

# 或者设置自动清理
find reports/ -type d -mtime +30 -exec rm -rf {} \;
```

## 故障排除

### 1. 权限问题

```bash
# 确保脚本有执行权限
chmod +x generate_report.py
chmod +x auto_report_schedule.sh

# 确保输出目录可写
chmod 755 reports/
chmod 755 static/reports/
```

### 2. 路径问题

```bash
# 在 crontab 中使用绝对路径
0 * * * * cd /full/path/to/FastChat && /usr/bin/python generate_report.py
```

### 3. 环境变量问题

```bash
# 在 crontab 中设置环境变量
PATH=/usr/local/bin:/usr/bin:/bin
0 * * * * cd /path/to/FastChat && python generate_report.py
```

### 4. 虚拟环境问题

```bash
# 激活虚拟环境后运行
0 * * * * cd /path/to/FastChat && source venv/bin/activate && python generate_report.py
```

## 性能优化建议

### 1. 合理设置更新频率

- **高频更新场景**（每5-15分钟）：适用于活跃的投票系统
- **中频更新场景**（每30分钟-1小时）：适用于中等活跃度的系统
- **低频更新场景**（每天1-2次）：适用于低活跃度的系统

### 2. 资源优化

```bash
# 只生成HTML报告（减少处理时间）
python generate_report.py --html-only

# 只生成摘要报告（减少文件大小）
python generate_report.py --summary-only
```

### 3. 存储优化

```bash
# 定期清理旧报告
python generate_report.py --cleanup-days 7

# 或者在 crontab 中设置
0 2 * * 0 cd /path/to/FastChat && python generate_report.py --cleanup-days 7
```

## 集成建议

### 1. Web 服务器集成

```bash
# 将报告目录软链接到 Web 服务器
ln -s /path/to/FastChat/static/reports /var/www/html/fastchat-reports

# 设置适当的权限
chown -R www-data:www-data /var/www/html/fastchat-reports
```

### 2. 监控集成

```bash
# 使用 Prometheus 监控报告生成
echo "fastchat_report_generated $(date +%s)" > /var/lib/prometheus/node-exporter/fastchat_report.prom
```

### 3. 通知集成

```bash
# Slack 通知
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"FastChat 投票分析报告已更新"}' \
  YOUR_SLACK_WEBHOOK_URL
```

## 总结

通过以上设置，您的 FastChat 投票分析报告将：

1. ✅ **自动检测最新数据** - 无需手动指定日志文件
2. ✅ **定时自动更新** - 确保报告始终包含最新投票数据
3. ✅ **灵活的更新频率** - 根据需要调整更新间隔
4. ✅ **完整的日志记录** - 便于监控和故障排除
5. ✅ **自动清理机制** - 防止存储空间被占满

现在您再也不用担心投票分析报告不包含最新数据的问题了！ 