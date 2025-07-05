#!/bin/bash

# FastChat 手动更新报告脚本
# 用于手动或通过其他方式触发报告更新

echo "🔄 手动更新 FastChat 报告"
echo "================================"

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 运行报告生成
echo "📊 正在生成最新报告..."
python generate_report.py

echo ""
echo "✅ 报告更新完成！"
echo "📁 查看最新报告: open static/reports/report.html"
echo "📋 查看报告目录: ls -la reports/"
echo ""
echo "💡 提示: 如需自动更新，请运行以下命令定期执行此脚本"
echo "   例如: watch -n 900 ./update_report.sh  # 每15分钟更新一次" 