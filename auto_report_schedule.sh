#!/bin/bash

# FastChat 自动报告生成定时任务脚本
# 此脚本用于定期生成最新的投票分析报告

# 设置项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 设置日志文件
LOG_FILE="$PROJECT_DIR/auto_report.log"

# 记录开始时间
echo "$(date '+%Y-%m-%d %H:%M:%S') - 开始自动报告生成" >> "$LOG_FILE"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 已激活虚拟环境" >> "$LOG_FILE"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 已激活虚拟环境" >> "$LOG_FILE"
fi

# 运行报告生成脚本
echo "$(date '+%Y-%m-%d %H:%M:%S') - 正在生成报告..." >> "$LOG_FILE"
python generate_report.py >> "$LOG_FILE" 2>&1

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 报告生成成功" >> "$LOG_FILE"
    
    # 可选：发送通知邮件
    # echo "FastChat 投票分析报告已更新 - $(date)" | mail -s "FastChat 报告更新" your-email@example.com
    
    # 可选：复制到Web服务器目录
    # cp -r reports/$(ls -t reports/ | head -1)/* /var/www/html/fastchat-reports/
    
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 报告生成失败" >> "$LOG_FILE"
    
    # 可选：发送错误通知
    # echo "FastChat 投票分析报告生成失败 - $(date)" | mail -s "FastChat 报告生成失败" admin@example.com
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - 自动报告生成完成" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

# 清理旧日志（保留最近7天）
find "$PROJECT_DIR" -name "auto_report.log" -mtime +7 -delete 2>/dev/null

exit 0 