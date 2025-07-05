#!/bin/bash

# FastChat 投票分析报告状态检查脚本
# 用于检查报告生成系统的运行状态

# 获取当前脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔍 FastChat 投票分析报告状态检查"
echo "==============================================="
echo "检查时间: $(date)"
echo "项目目录: $SCRIPT_DIR"
echo ""

# 检查必要文件是否存在
echo "📁 文件检查:"
files_to_check=(
    "generate_report.py"
    "auto_report_schedule.sh"
    "setup_crontab.sh"
    "vote_analysis.py"
)

for file in "${files_to_check[@]}"; do
    if [[ -f "$SCRIPT_DIR/$file" ]]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (缺失)"
    fi
done
echo ""

# 检查目录结构
echo "📂 目录结构检查:"
directories_to_check=(
    "reports"
    "static/reports"
)

for dir in "${directories_to_check[@]}"; do
    if [[ -d "$SCRIPT_DIR/$dir" ]]; then
        echo "  ✅ $dir/"
    else
        echo "  ❌ $dir/ (缺失)"
        mkdir -p "$SCRIPT_DIR/$dir"
        echo "    🔧 已创建目录: $dir/"
    fi
done
echo ""

# 检查日志文件
echo "📄 日志文件检查:"
log_files=($(ls -1 "$SCRIPT_DIR"/*-conv.json 2>/dev/null))
if [[ ${#log_files[@]} -gt 0 ]]; then
    echo "  找到 ${#log_files[@]} 个日志文件:"
    for log_file in "${log_files[@]}"; do
        filename=$(basename "$log_file")
        size=$(du -h "$log_file" | cut -f1)
        modified=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$log_file" 2>/dev/null || stat -c "%y" "$log_file" 2>/dev/null | cut -d'.' -f1)
        echo "    📄 $filename ($size, 修改时间: $modified)"
    done
    
    # 显示最新的日志文件
    latest_log=$(ls -t "$SCRIPT_DIR"/*-conv.json 2>/dev/null | head -1)
    if [[ -n "$latest_log" ]]; then
        echo "  🔄 最新日志文件: $(basename "$latest_log")"
    fi
else
    echo "  ❌ 未找到日志文件 (*-conv.json)"
fi
echo ""

# 检查最近生成的报告
echo "📊 报告生成检查:"
if [[ -d "$SCRIPT_DIR/reports" ]]; then
    recent_reports=($(ls -1t "$SCRIPT_DIR/reports" 2>/dev/null | head -5))
    if [[ ${#recent_reports[@]} -gt 0 ]]; then
        echo "  最近生成的报告 (最多显示5个):"
        for report_dir in "${recent_reports[@]}"; do
            if [[ -d "$SCRIPT_DIR/reports/$report_dir" ]]; then
                echo "    📁 $report_dir"
                # 检查报告文件
                report_files=(
                    "report.html"
                    "summary.md"
                    "vote_analysis.csv"
                    "elo_rankings.csv"
                )
                for report_file in "${report_files[@]}"; do
                    if [[ -f "$SCRIPT_DIR/reports/$report_dir/$report_file" ]]; then
                        echo "      ✅ $report_file"
                    else
                        echo "      ❌ $report_file (缺失)"
                    fi
                done
            fi
        done
    else
        echo "  ❌ 未找到生成的报告"
    fi
else
    echo "  ❌ 报告目录不存在"
fi
echo ""

# 检查定时任务
echo "⏰ 定时任务检查:"
crontab_entries=$(crontab -l 2>/dev/null | grep -E "FastChat|generate_report|auto_report_schedule")
if [[ -n "$crontab_entries" ]]; then
    echo "  找到相关的定时任务:"
    echo "$crontab_entries" | while read -r line; do
        echo "    📅 $line"
    done
else
    echo "  ❌ 未找到相关的定时任务"
    echo "    💡 提示: 运行 ./setup_crontab.sh 来设置定时任务"
fi
echo ""

# 检查最新的自动报告日志
echo "📋 自动报告日志检查:"
if [[ -f "$SCRIPT_DIR/auto_report.log" ]]; then
    echo "  ✅ 找到自动报告日志文件"
    log_size=$(du -h "$SCRIPT_DIR/auto_report.log" | cut -f1)
    echo "    📏 文件大小: $log_size"
    
    # 显示最后几行日志
    echo "  📄 最近的日志记录:"
    tail -5 "$SCRIPT_DIR/auto_report.log" | while read -r line; do
        echo "    $line"
    done
else
    echo "  ❌ 未找到自动报告日志文件"
    echo "    💡 提示: 运行 ./auto_report_schedule.sh 来生成日志"
fi
echo ""

# 检查系统资源
echo "💻 系统资源检查:"
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version 2>&1)
    echo "  ✅ Python: $python_version"
else
    echo "  ❌ Python3 未安装"
fi

if command -v crontab >/dev/null 2>&1; then
    echo "  ✅ Crontab: 可用"
else
    echo "  ❌ Crontab: 不可用"
fi

# 检查磁盘空间
disk_usage=$(df -h "$SCRIPT_DIR" | tail -1 | awk '{print $5}')
echo "  💾 磁盘使用率: $disk_usage"
echo ""

# 提供建议
echo "💡 建议和下一步操作:"
echo "==============================================="

# 检查是否需要设置定时任务
if [[ -z "$crontab_entries" ]]; then
    echo "🔧 建议设置定时任务:"
    echo "  运行: ./setup_crontab.sh"
    echo ""
fi

# 检查是否有最新数据
if [[ -n "$latest_log" ]]; then
    echo "🔄 手动生成最新报告:"
    echo "  运行: python generate_report.py"
    echo ""
fi

# 检查报告访问
if [[ -f "$SCRIPT_DIR/static/reports/report.html" ]]; then
    echo "🌐 查看最新报告:"
    echo "  浏览器访问: file://$SCRIPT_DIR/static/reports/report.html"
    echo "  或运行: open $SCRIPT_DIR/static/reports/report.html"
    echo ""
fi

echo "📊 监控命令:"
echo "  实时查看日志: tail -f auto_report.log"
echo "  检查定时任务: crontab -l"
echo "  查看系统日志: tail -f /var/log/system.log | grep cron"
echo ""

echo "✅ 状态检查完成!" 