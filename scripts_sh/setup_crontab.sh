#!/bin/bash

# FastChat 投票分析报告定时任务设置脚本
# 用于快速配置 crontab 定时任务

# 获取当前脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 FastChat 投票分析报告定时任务设置"
echo "==============================================="
echo "当前项目目录: $SCRIPT_DIR"
echo ""

# 检查必要文件是否存在
if [[ ! -f "$SCRIPT_DIR/scripts_py/generate_report.py" ]]; then
    echo "❌ 错误: 未找到 generate_report.py 文件"
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/auto_report_schedule.sh" ]]; then
    echo "❌ 错误: 未找到 auto_report_schedule.sh 文件"
    exit 1
fi

# 确保脚本有执行权限
chmod +x "$SCRIPT_DIR/scripts_py/generate_report.py"
chmod +x "$SCRIPT_DIR/auto_report_schedule.sh"

echo "✅ 脚本权限检查完成"
echo ""

# 显示当前的 crontab 设置
echo "📋 当前的 crontab 设置:"
crontab -l 2>/dev/null || echo "  (无定时任务)"
echo ""

# 提供不同的定时任务选项
echo "请选择定时任务频率:"
echo "1) 每5分钟更新一次 (实时监控)"
echo "2) 每15分钟更新一次 (推荐)"
echo "3) 每30分钟更新一次"
echo "4) 每小时更新一次"
echo "5) 每天更新一次 (凌晨2点)"
echo "6) 自定义设置"
echo "7) 移除现有的 FastChat 定时任务"
echo "8) 退出"
echo ""

read -p "请输入选项 (1-8): " choice

case $choice in
    1)
        CRON_SCHEDULE="*/5 * * * *"
        DESCRIPTION="每5分钟更新一次"
        ;;
    2)
        CRON_SCHEDULE="*/15 * * * *"
        DESCRIPTION="每15分钟更新一次"
        ;;
    3)
        CRON_SCHEDULE="*/30 * * * *"
        DESCRIPTION="每30分钟更新一次"
        ;;
    4)
        CRON_SCHEDULE="0 * * * *"
        DESCRIPTION="每小时更新一次"
        ;;
    5)
        CRON_SCHEDULE="0 2 * * *"
        DESCRIPTION="每天凌晨2点更新一次"
        ;;
    6)
        echo "请输入 cron 表达式 (例如: */15 * * * *):"
        read -p "cron 表达式: " CRON_SCHEDULE
        DESCRIPTION="自定义: $CRON_SCHEDULE"
        ;;
    7)
        echo "🗑️ 移除现有的 FastChat 定时任务..."
        crontab -l 2>/dev/null | grep -v "FastChat\|generate_report\|auto_report_schedule" | crontab -
        echo "✅ 已移除现有的 FastChat 定时任务"
        exit 0
        ;;
    8)
        echo "👋 退出设置"
        exit 0
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 构建完整的 crontab 命令
CRON_COMMAND="$CRON_SCHEDULE cd $SCRIPT_DIR && $SCRIPT_DIR/auto_report_schedule.sh"

echo ""
echo "📝 准备添加的定时任务:"
echo "  频率: $DESCRIPTION"
echo "  命令: $CRON_COMMAND"
echo ""

read -p "确认添加此定时任务? (y/N): " confirm

if [[ $confirm =~ ^[Yy]$ ]]; then
    # 备份现有的 crontab
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
    
    # 添加新的定时任务
    (crontab -l 2>/dev/null; echo "# FastChat 投票分析报告自动生成 - $DESCRIPTION"; echo "$CRON_COMMAND") | crontab -
    
    echo "✅ 定时任务已成功添加!"
    echo ""
    echo "📋 当前的 crontab 设置:"
    crontab -l | grep -A1 -B1 "FastChat"
    echo ""
    echo "🔍 验证定时任务:"
    echo "  查看系统日志: tail -f /var/log/system.log | grep cron"
    echo "  查看生成日志: tail -f $SCRIPT_DIR/auto_report.log"
    echo "  手动测试: $SCRIPT_DIR/auto_report_schedule.sh"
    echo ""
    echo "📊 查看报告:"
    echo "  最新报告: ls -lt $SCRIPT_DIR/reports/ | head -5"
    echo "  Web访问: open $SCRIPT_DIR/static/reports/report.html"
    echo ""
    echo "🎉 设置完成! 系统将按照设定的频率自动生成投票分析报告。"
else
    echo "❌ 取消添加定时任务"
fi 