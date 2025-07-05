#!/usr/bin/env python3
"""
FastChat 一键报告生成脚本
自动分析投票数据并生成HTML报告和摘要
支持ELO排名计算和数据可视化
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
import glob
import locale
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import base64
from io import BytesIO
import numpy as np

# 语言本地化配置
def get_system_language():
    """获取系统语言设置"""
    try:
        # 尝试获取系统语言
        lang = locale.getdefaultlocale()[0]
        if lang and lang.startswith('zh'):
            return 'zh'
        else:
            return 'en'
    except:
        # 如果获取失败，默认使用英文
        return 'en'

# 多语言文本配置
TEXTS = {
    'zh': {
        'script_title': '🚀 FastChat 一键报告生成脚本',
        'separator': '=' * 50,
        'using_log_file': '📄 使用日志文件: {}',
        'log_file_not_found': '❌ 指定的日志文件不存在: {}',
        'no_matching_log': '❌ 未找到匹配的日志文件: {}',
        'analyzing_vote_data': '📊 开始分析投票数据: {}',
        'vote_analysis': '投票统计分析',
        'elo_analysis': 'ELO排名分析',
        'analysis_complete': '✅ {} 完成',
        'analysis_failed': '❌ {} 失败: {}',
        'data_file_missing': '❌ 数据文件不存在: {}',
        'data_read_failed': '❌ 读取数据失败: {}',
        'report_generated': '✅ 报告已生成: {}',
        'summary_report': '📋 创建摘要报告...',
        'summary_generated': '✅ 摘要报告已生成: {}',
        'cleanup_old_reports': '🧹 清理{}天前的旧报告...',
        'deleted_old_report': '🗑️  已删除旧报告: {}',
        'delete_failed': '⚠️  删除失败: {} - {}',
        'report_complete': '✅ 报告生成完成！',
        'archive_dir': '📁 归档目录: {}',
        'generated_files': '📊 生成的文件:',
        'view_html_report': '🌐 查看HTML报告: open {}',
        'next_run_time': '⏰ 下次运行时间: {}',
        'crontab_tip': '💡 提示: 可以将此脚本添加到crontab实现定时任务',
        'copied_to_static': '✅ 最新报告已复制到 static/reports/report.html',
        'report_not_found': '❌ 找不到报告文件: {}',
        'copy_failed': '❌ 复制报告到 static 目录失败: {}',
        'data_analysis_failed': '❌ 数据分析失败',
        'analyzing_cumulative_data': '📊 开始分析累积投票数据...',
        'logs_archive_not_found': '❌ 未找到日志归档目录: {}',
        'no_historical_logs': '❌ 未找到历史日志文件: {}',
        'cumulative_vote_analysis': '📊 累积投票分析',
        'cumulative_elo_analysis': '📊 累积ELO分析',
        'using_cumulative_analysis': '📊 使用累积历史数据分析模式',
        'cumulative_analysis_failed': '❌ 累积数据分析失败',
        
        # HTML报告文本
        'html_title': 'FastChat 投票分析报告',
        'report_title': '🚀 HKGAI 投票分析报告',
        'report_subtitle': '模型对战结果统计与ELO排名分析',
        'generation_time': '生成时间: {}',
        'total_votes': '总投票数',
        'participating_models': '参与模型数',
        'effective_battles': '有效对战数',
        'analysis_date': '分析日期',
        'vote_distribution': '投票类型分布',
        'model_winrate_comparison': '模型胜率对比',
        'elo_ranking_table': 'ELO排名表',
        'detailed_statistics_table': '详细统计表',
        'rank': '排名',
        'model_name': '模型名称',
        'elo_score': 'ELO评分',
        'total_battles': '总对战',
        'wins': '胜利',
        'losses': '失败',
        'ties': '平局',
        'win_rate': '胜率',
        'tie_rate': '平局率',
        'loss_rate': '失败率',
        'footer_generated': '报告生成时间: {} | 数据来源: FastChat Arena 投票系统',
        'footer_elo_info': 'ELO评级系统 | K因子: 32 | 置信区间: 95%',
        'footer_auto_info': '此报告由自动化脚本生成，支持定时更新',
        
        # 图表标签
        'left_wins': '左方获胜',
        'right_wins': '右方获胜',
        'ties_chart': '平局',
        'vote_type_distribution': '投票类型分布',
        'model_winrate_chart': '模型胜率对比',
        'win_rate_label': '胜率 (%)',
        'chart_gen_failed': '图表生成失败'
    },
    'en': {
        'script_title': '🚀 FastChat One-Click Report Generation Script',
        'separator': '=' * 50,
        'using_log_file': '📄 Using log file: {}',
        'log_file_not_found': '❌ Specified log file does not exist: {}',
        'no_matching_log': '❌ No matching log file found: {}',
        'analyzing_vote_data': '📊 Starting vote data analysis: {}',
        'vote_analysis': 'Vote Statistics Analysis',
        'elo_analysis': 'ELO Ranking Analysis',
        'analysis_complete': '✅ {} completed',
        'analysis_failed': '❌ {} failed: {}',
        'data_file_missing': '❌ Data file does not exist: {}',
        'data_read_failed': '❌ Failed to read data: {}',
        'report_generated': '✅ Report generated: {}',
        'summary_report': '📋 Creating summary report...',
        'summary_generated': '✅ Summary report generated: {}',
        'cleanup_old_reports': '🧹 Cleaning up reports older than {} days...',
        'deleted_old_report': '🗑️  Deleted old report: {}',
        'delete_failed': '⚠️  Failed to delete: {} - {}',
        'report_complete': '✅ Report generation completed!',
        'archive_dir': '📁 Archive directory: {}',
        'generated_files': '📊 Generated files:',
        'view_html_report': '🌐 View HTML report: open {}',
        'next_run_time': '⏰ Next run time: {}',
        'crontab_tip': '💡 Tip: You can add this script to crontab for scheduled tasks',
        'copied_to_static': '✅ Latest report copied to static/reports/report.html',
        'report_not_found': '❌ Report file not found: {}',
        'copy_failed': '❌ Failed to copy report to static directory: {}',
        'data_analysis_failed': '❌ Data analysis failed',
        'analyzing_cumulative_data': '📊 Starting cumulative vote data analysis...',
        'logs_archive_not_found': '❌ Log archive directory not found: {}',
        'no_historical_logs': '❌ No historical log files found: {}',
        'cumulative_vote_analysis': '📊 Cumulative Vote Analysis',
        'cumulative_elo_analysis': '📊 Cumulative ELO Analysis',
        'using_cumulative_analysis': '📊 Using cumulative historical data analysis mode',
        'cumulative_analysis_failed': '❌ Cumulative data analysis failed',
        
        # HTML报告文本
        'html_title': 'FastChat Vote Analysis Report',
        'report_title': '🚀 HKGAI Vote Analysis Report',
        'report_subtitle': 'Model Battle Results Statistics & ELO Ranking Analysis',
        'generation_time': 'Generated: {}',
        'total_votes': 'Total Votes',
        'participating_models': 'Participating Models',
        'effective_battles': 'Effective Battles',
        'analysis_date': 'Analysis Date',
        'vote_distribution': 'Vote Type Distribution',
        'model_winrate_comparison': 'Model Win Rate Comparison',
        'elo_ranking_table': 'ELO Ranking Table',
        'detailed_statistics_table': 'Detailed Statistics Table',
        'rank': 'Rank',
        'model_name': 'Model Name',
        'elo_score': 'ELO Score',
        'total_battles': 'Total Battles',
        'wins': 'Wins',
        'losses': 'Losses',
        'ties': 'Ties',
        'win_rate': 'Win Rate',
        'tie_rate': 'Tie Rate',
        'loss_rate': 'Loss Rate',
        'footer_generated': 'Report Generated: {} | Data Source: FastChat Arena Voting System',
        'footer_elo_info': 'ELO Rating System | K-Factor: 32 | Confidence Interval: 95%',
        'footer_auto_info': 'This report is automatically generated and supports scheduled updates',
        
        # 图表标签
        'left_wins': 'Left Wins',
        'right_wins': 'Right Wins',
        'ties_chart': 'Ties',
        'vote_type_distribution': 'Vote Type Distribution',
        'model_winrate_chart': 'Model Win Rate Comparison',
        'win_rate_label': 'Win Rate (%)',
        'chart_gen_failed': 'Chart generation failed'
    }
}

# 获取当前语言
CURRENT_LANG = get_system_language()

def t(key):
    """获取本地化文本"""
    return TEXTS[CURRENT_LANG].get(key, TEXTS['en'].get(key, key))

def run_command(cmd, description):
    """运行命令并处理错误"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(t('analysis_complete').format(description))
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(t('analysis_failed').format(description, e))
        print(f"错误输出: {e.stderr}")
        return None

def find_latest_log_file(log_dir=".", pattern="*-conv.json"):
    """查找最新的日志文件"""
    log_files = list(Path(log_dir).glob(pattern))
    if not log_files:
        return None
    
    # 按修改时间排序，返回最新的
    latest_file = max(log_files, key=lambda x: x.stat().st_mtime)
    return latest_file

def check_log_file_changes(log_file):
    """检查日志文件是否有新数据"""
    if not log_file or not Path(log_file).exists():
        return False, None, None
    
    log_path = Path(log_file)
    
    # 获取文件修改时间和大小
    current_mtime = log_path.stat().st_mtime
    current_size = log_path.stat().st_size
    
    # 检查是否有之前的记录
    cache_file = Path(".log_cache.json")
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            last_file = cache_data.get('last_file')
            last_mtime = cache_data.get('last_mtime')
            last_size = cache_data.get('last_size')
            
            # 如果是同一个文件且修改时间和大小都没变，说明没有新数据
            if (last_file == str(log_path) and 
                last_mtime == current_mtime and 
                last_size == current_size):
                return False, last_mtime, last_size
        except (json.JSONDecodeError, KeyError):
            pass
    
    # 更新缓存
    cache_data = {
        'last_file': str(log_path),
        'last_mtime': current_mtime,
        'last_size': current_size,
        'last_check': datetime.now().isoformat()
    }
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False)
    
    return True, current_mtime, current_size

def count_vote_entries(log_file):
    """统计日志文件中的投票条目数量"""
    if not log_file or not Path(log_file).exists():
        return 0, 0, 0, 0, 0
    
    vote_types = {'leftvote': 0, 'rightvote': 0, 'tievote': 0, 'bothbad_vote': 0, 'total': 0}
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    vote_type = data.get('type', '')
                    if vote_type in ['leftvote', 'rightvote', 'tievote', 'bothbad_vote']:
                        vote_types[vote_type] += 1
                        vote_types['total'] += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass
    
    return vote_types['leftvote'], vote_types['rightvote'], vote_types['tievote'], vote_types['bothbad_vote'], vote_types['total']

def analyze_cumulative_vote_data():
    """分析累积的历史投票数据"""
    print(t('analyzing_cumulative_data'))
    
    # 获取主目录路径
    main_dir = Path(__file__).parent.resolve()
    logs_archive_dir = main_dir / 'logs_archive'
    
    # 收集所有日志文件
    all_log_files = []
    
    # 1. 从logs_archive目录获取历史日志文件
    if logs_archive_dir.exists():
        archive_files = list(logs_archive_dir.glob('*.json'))
        all_log_files.extend(archive_files)
        print(f"Found {len(archive_files)} archived log files in {logs_archive_dir}")
    else:
        print(f"⚠️  Archive directory not found: {logs_archive_dir}")
    
    # 2. 从根目录获取最新日志文件（包含当前数据）
    root_log_files = list(main_dir.glob('*-conv.json'))
    if root_log_files:
        print(f"Found {len(root_log_files)} current log files in root directory")
        for root_file in root_log_files:
            # 检查是否已经在archive中存在相同的文件
            archive_equivalent = logs_archive_dir / root_file.name if logs_archive_dir.exists() else None
            if not archive_equivalent or not archive_equivalent.exists():
                all_log_files.append(root_file)
                print(f"  + Including current log: {root_file.name}")
            else:
                # 比较文件大小和修改时间，使用更新的文件
                root_mtime = root_file.stat().st_mtime
                archive_mtime = archive_equivalent.stat().st_mtime
                root_size = root_file.stat().st_size
                archive_size = archive_equivalent.stat().st_size
                
                if root_mtime > archive_mtime or root_size != archive_size:
                    # 根目录的文件更新，替换archive中的文件
                    all_log_files = [f for f in all_log_files if f.name != root_file.name]
                    all_log_files.append(root_file)
                    print(f"  + Using newer current log: {root_file.name} (newer than archived version)")
                else:
                    print(f"  - Skipping current log: {root_file.name} (same as archived version)")
    
    if not all_log_files:
        print("❌ No log files found in either logs_archive or root directory")
        return [], [], {}
    
    # 按文件名排序（通常对应日期）
    all_log_files.sort(key=lambda x: x.name)
    print(f"\n📊 Total log files to process: {len(all_log_files)}")
    for log_file in all_log_files:
        print(f"  - {log_file.name} ({log_file.parent.name if log_file.parent.name != main_dir.name else 'root'})")
    
    # 创建临时合并文件
    temp_merged_file = main_dir / 'temp_merged_logs.json'
    
    try:
        # 合并所有日志文件
        with open(temp_merged_file, 'w', encoding='utf-8') as merged_file:
            for log_file in all_log_files:
                print(f"Processing {log_file.name}...")
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            merged_file.write(line)
                except Exception as e:
                    print(f"⚠️  Error processing {log_file.name}: {e}")
                    continue
        
        print(f"Merged {len(all_log_files)} files into {temp_merged_file}")
        
        # 运行投票分析
        cmd = f"python {main_dir}/vote_analysis.py --log-file {temp_merged_file} --export"
        output = run_command(cmd, t('cumulative_vote_analysis'))
        
        # 运行ELO分析
        cmd = f"python {main_dir}/elo_analysis_simple.py --log-file {temp_merged_file} --export"
        output = run_command(cmd, t('cumulative_elo_analysis'))
        
        # 读取生成的数据文件
        try:
            # 读取投票分析数据 - 从当前工作目录读取（归档目录）
            vote_file = Path('vote_analysis.csv')
            with open(vote_file, 'r', encoding='utf-8') as f:
                vote_data = f.read()
            
            # 读取ELO排名数据
            elo_file = Path('elo_rankings.csv')
            with open(elo_file, 'r', encoding='utf-8') as f:
                elo_data = f.read()
                
            # 读取投票分布数据
            distribution_file = Path('vote_distribution.json')
            with open(distribution_file, 'r', encoding='utf-8') as f:
                distribution_data = json.load(f)
                
            # 解析CSV数据
            vote_lines = vote_data.strip().split('\n')
            vote_headers = vote_lines[0].split(',')
            vote_rows = [dict(zip(vote_headers, line.split(','))) for line in vote_lines[1:]]
            
            elo_lines = elo_data.strip().split('\n')
            elo_headers = elo_lines[0].split(',')
            elo_rows = [dict(zip(elo_headers, line.split(','))) for line in elo_lines[1:]]
            
            return vote_rows, elo_rows, distribution_data
            
        except FileNotFoundError as e:
            print(t('data_file_missing').format(e))
            return [], [], {}
        except Exception as e:
            print(t('data_read_failed').format(e))
            return [], [], {}
    
    finally:
        # 清理临时文件
        if temp_merged_file.exists():
            temp_merged_file.unlink()
            print(f"Cleaned up temporary file: {temp_merged_file}")

def analyze_vote_data(log_file):
    """分析投票数据"""
    print(t('analyzing_vote_data').format(log_file))
    
    # 获取主目录路径
    main_dir = Path(__file__).parent.resolve()
    
    # 在强制模式下，清除旧的数据文件，确保重新分析
    if hasattr(analyze_vote_data, '_force_mode') and analyze_vote_data._force_mode:
        print("🔄 强制模式：清除旧数据文件，重新分析最新数据")
        old_files = [
            main_dir / 'vote_analysis.csv',
            main_dir / 'elo_rankings.csv', 
            main_dir / 'vote_distribution.json'
        ]
        for old_file in old_files:
            if old_file.exists():
                try:
                    old_file.unlink()
                    print(f"🗑️  已删除旧文件: {old_file.name}")
                except Exception as e:
                    print(f"⚠️  删除文件失败: {old_file.name} - {e}")
    
    # 运行投票分析
    cmd = f"python {main_dir}/vote_analysis.py --log-file {log_file} --export"
    output = run_command(cmd, t('vote_analysis'))
    
    # 运行ELO分析
    cmd = f"python {main_dir}/elo_analysis_simple.py --log-file {log_file} --export"
    output = run_command(cmd, t('elo_analysis'))
    
    # 读取生成的数据文件 - 从当前工作目录读取（归档目录）
    try:
        # 读取投票分析数据
        vote_file = Path('vote_analysis.csv')
        with open(vote_file, 'r', encoding='utf-8') as f:
            vote_data = f.read()
        
        # 读取ELO排名数据
        elo_file = Path('elo_rankings.csv')
        with open(elo_file, 'r', encoding='utf-8') as f:
            elo_data = f.read()
            
        # 读取投票分布数据
        distribution_file = Path('vote_distribution.json')
        with open(distribution_file, 'r', encoding='utf-8') as f:
            distribution_data = json.load(f)
            
        # 解析CSV数据
        vote_lines = vote_data.strip().split('\n')
        vote_headers = vote_lines[0].split(',')
        vote_rows = [dict(zip(vote_headers, line.split(','))) for line in vote_lines[1:]]
        
        elo_lines = elo_data.strip().split('\n')
        elo_headers = elo_lines[0].split(',')
        elo_rows = [dict(zip(elo_headers, line.split(','))) for line in elo_lines[1:]]
        
        return vote_rows, elo_rows, distribution_data
        
    except FileNotFoundError as e:
        print(t('data_file_missing').format(e))
        return [], [], {}
    except Exception as e:
        print(t('data_read_failed').format(e))
        return [], [], {}

def create_report_html(data_source, vote_rows, elo_rows, distribution_data):
    """创建报告HTML页面"""
    
    # 生成图表
    vote_chart_img = generate_vote_distribution_chart(distribution_data)
    winrate_chart_img = generate_winrate_chart(vote_rows)
    
    # 获取时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 确定数据源显示文本
    if data_source == "累积历史数据":
        data_source_text = "累积历史数据 (所有归档日志)"
        report_title = "FastChat 累积投票分析报告"
    else:
        data_source_text = f"单一日志文件: {Path(data_source).name}"
        report_title = "FastChat 投票分析报告"
    
    # 创建HTML内容
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        :root {{
            --primary-color: #1976D2;
            --secondary-color: #63A4FF;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
        }}
        
        /* 默认浅色模式 */
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #ffffff;
            color: #333333;
            line-height: 1.6;
            transition: background-color 0.3s ease, color 0.3s ease;
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 30px 20px;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white !important;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            color: white !important;
        }}
        
        .header p {{
            font-size: 1.2em;
            opacity: 0.9;
            color: white !important;
        }}
        
        .content {{
            background-color: #ffffff;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            border: 1px solid #e0e0e0;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr); /* 固定4列，防止换行 */
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white !important;
            padding: 15px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }}
        
        .stat-number {{
            font-size: clamp(1.2em, 2vw, 2em); /* 内容自适应缩放，防止溢出换行 */
            font-weight: bold;
            margin-bottom: 5px;
            color: white !important;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
            color: white !important;
        }}
        
        .stat-number-date, .stat-number {{
            font-size: 2em !important;
            font-weight: bold;
            color: white !important;
        }}
        .stat-card {{
            min-height: 90px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .chart-container {{
            background-color: #ffffff;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            text-align: center;
            border: 1px solid #e0e0e0;
        }}
        
        .chart-title {{
            text-align: center;
            margin-bottom: 15px;
            color: #333333;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        .table-container {{
            background-color: #ffffff;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            margin-bottom: 15px;
            border: 1px solid #e0e0e0;
        }}
        
        .table-title {{
            text-align: center;
            margin-bottom: 15px;
            color: #333333;
            font-size: 1.1em;
            font-weight: 600;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        th {{
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white !important;
            font-weight: 600;
            font-size: 0.9em;
        }}
        
        td {{
            font-size: 0.9em;
            color: #333333;
        }}
        
        tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .winner {{
            color: var(--success-color) !important;
            font-weight: bold;
        }}
        
        .loser {{
            color: var(--danger-color) !important;
        }}
        
        .tie {{
            color: var(--warning-color) !important;
            font-weight: bold;
        }}
        
        .footer {{
            background-color: #ffffff;
            padding: 20px;
            text-align: center;
            color: #333333;
            border-radius: 15px;
            margin-top: 30px;
            border: 1px solid #e0e0e0;
            opacity: 0.8;
        }}
        
        /* 深色模式 - 系统自动检测 */
        @media (prefers-color-scheme: dark) {{
            body {{
                background-color: #1a1a1a !important;
                color: #ffffff !important;
            }}
            
            .content {{
                background-color: #2d2d2d !important;
                border-color: #404040 !important;
                color: #ffffff !important;
            }}
            
            .chart-container {{
                background-color: #2d2d2d !important;
                border-color: #404040 !important;
                color: #ffffff !important;
            }}
            
            .table-container {{
                background-color: #2d2d2d !important;
                border-color: #404040 !important;
                color: #ffffff !important;
            }}
            
            .footer {{
                background-color: #2d2d2d !important;
                border-color: #404040 !important;
                color: #ffffff !important;
            }}
            
            .chart-title, .table-title {{
                color: #ffffff !important;
            }}
            
            /* 表格样式强化 */
            table {{
                color: #ffffff !important;
                background-color: transparent !important;
            }}
            
            th {{
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
                color: white !important;
                border-bottom-color: #404040 !important;
            }}
            
            td {{
                color: #ffffff !important;
                background-color: transparent !important;
            }}
            
            tbody tr {{
                color: #ffffff !important;
                background-color: transparent !important;
            }}
            
            tbody td {{
                color: #ffffff !important;
                background-color: transparent !important;
            }}
            
            thead th {{
                color: white !important;
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
            }}
            
            th, td {{
                border-bottom-color: #404040 !important;
            }}
            
            tr:hover {{
                background-color: #3d3d3d !important;
            }}
            
            tr:hover td {{
                color: #ffffff !important;
            }}
            
            /* 修复过度的通用样式 - 只针对特定文本元素 */
            .content p, .content span, .content div:not(.stat-card):not(.header):not(.chart-container):not(.table-container) {{
                color: #ffffff !important;
            }}
            
            .content h1:not(.header h1), .content h2, .content h3, .content h4, .content h5, .content h6 {{
                color: #ffffff !important;
            }}
            
            /* 统计卡片保持原有样式 */
            .stat-card {{
                background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%) !important;
            }}
            
            .stat-number, .stat-label {{
                color: white !important;
            }}
            
            /* 状态颜色在深色模式下保持可见性 */
            .winner {{
                color: #66bb6a !important;
                font-weight: bold !important;
            }}
            
            .loser {{
                color: #ef5350 !important;
                font-weight: bold !important;
            }}
            
            .tie {{
                color: #ffca28 !important;
                font-weight: bold !important;
            }}
            
            /* 保持特殊元素的颜色 */
            .content .stat-card * {{
                color: white !important;
            }}
            
            .content .header * {{
                color: white !important;
            }}
            
            .content .winner {{
                color: #66bb6a !important;
            }}
            
            .content .loser {{
                color: #ef5350 !important;
            }}
            
            .content .tie {{
                color: #ffca28 !important;
            }}
            
            .content th {{
                color: white !important;
            }}
        }}
        
        /* 浅色模式 - 明确指定，确保在刷新时不会出现黑色覆盖 */
        @media (prefers-color-scheme: light) {{
            body {{
                background-color: #ffffff !important;
                color: #333333 !important;
            }}
            
            .content {{
                background-color: #ffffff !important;
                border-color: #e0e0e0 !important;
                color: #333333 !important;
            }}
            
            .chart-container {{
                background-color: #ffffff !important;
                border-color: #e0e0e0 !important;
                color: #333333 !important;
            }}
            
            .table-container {{
                background-color: #ffffff !important;
                border-color: #e0e0e0 !important;
                color: #333333 !important;
            }}
            
            .footer {{
                background-color: #ffffff !important;
                border-color: #e0e0e0 !important;
                color: #333333 !important;
            }}
            
            .chart-title, .table-title {{
                color: #333333 !important;
            }}
            
            td {{
                color: #333333 !important;
            }}
            
            th, td {{
                border-bottom-color: #e0e0e0 !important;
            }}
            
            tr:hover {{
                background-color: #f8f9fa !important;
            }}
            
            /* 确保浅色模式下文本为深色 */
            .content p, .content span, .content div:not(.stat-card):not(.header):not(.chart-container):not(.table-container) {{
                color: #333333 !important;
            }}
            
            .content h1:not(.header h1), .content h2, .content h3, .content h4, .content h5, .content h6 {{
                color: #333333 !important;
            }}
            
            /* 表格内容强制深色 */
            table {{
                color: #333333 !important;
            }}
            
            tbody tr {{
                color: #333333 !important;
            }}
            
            tbody td {{
                color: #333333 !important;
            }}
        }}
        
        /* 默认样式 - 当系统主题检测失败时的备用样式 */
        @media not all and (prefers-color-scheme: dark) {{
            body {{
                background-color: #ffffff;
                color: #333333;
            }}
            
            .content {{
                background-color: #ffffff;
                border-color: #e0e0e0;
                color: #333333;
            }}
            
            .chart-container {{
                background-color: #ffffff;
                border-color: #e0e0e0;
                color: #333333;
            }}
            
            .table-container {{
                background-color: #ffffff;
                border-color: #e0e0e0;
                color: #333333;
            }}
            
            .footer {{
                background-color: #ffffff;
                border-color: #e0e0e0;
                color: #333333;
            }}
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .header h1 {{
                font-size: 2em;
            }}
        }}
        
        .stat-number-date {{
            font-size: 1.1em !important;
            max-width: 90px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 {report_title}</h1>
            <p>模型对战结果统计与ELO排名分析</p>
            <p style="font-size: 0.9em; margin-top: 10px;">生成时间: {timestamp}</p>
            <p style="font-size: 0.8em; margin-top: 5px;">数据源: {data_source_text}</p>
        </div>
        <div class="content">
            <!-- 统计概览 -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{distribution_data.get('leftvote', 0) + distribution_data.get('rightvote', 0) + distribution_data.get('tievote', 0) + distribution_data.get('bothbad_vote', 0)}</div>
                    <div class="stat-label">总投票数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(vote_rows)}</div>
                    <div class="stat-label">参与模型数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{distribution_data.get('leftvote', 0) + distribution_data.get('rightvote', 0) + distribution_data.get('tievote', 0)}</div>
                    <div class="stat-label">有效对战数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{timestamp.split()[0]}</div>
                    <div class="stat-label">分析日期</div>
                </div>
            </div>
            <!-- 图表区域 -->
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">投票类型分布</div>
                    {vote_chart_img}
                </div>
                <div class="chart-container">
                    <div class="chart-title">模型胜率对比</div>
                    {winrate_chart_img}
                </div>
            </div>
            <!-- ELO排名表格 -->
            <div class="table-container">
                <div class="table-title">ELO排名表</div>
                <table id="eloTable">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>模型名称</th>
                            <th>ELO评分</th>
                            <th>总对战</th>
                            <th>胜利</th>
                            <th>失败</th>
                            <th>平局</th>
                            <th>胜率</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    # 添加ELO表格数据
    for i, row in enumerate(elo_rows):
        rank = i + 1
        is_winner = rank == 1
        win_rate = round(float(row['win_rate']), 2)
        html_content += f"""
                        <tr>
                            <td>{rank}</td>
                            <td class="{'winner' if is_winner else ''}">{row['model']}</td>
                            <td class="{'winner' if is_winner else ''}">{row['elo_rating']}</td>
                            <td>{row['total_battles']}</td>
                            <td class="winner">{row['wins']}</td>
                            <td class="loser">{row['losses']}</td>
                            <td class="tie">{row['ties']}</td>
                            <td class="{'winner' if is_winner else ''}">{win_rate:.2f}%</td>
                        </tr>"""
    
    html_content += """
                    </tbody>
                </table>
            </div>

            <!-- 详细统计表格 -->
            <div class="table-container">
                <div class="table-title">详细统计表</div>
                <table id="detailTable">
                    <thead>
                        <tr>
                            <th>模型名称</th>
                            <th>总对战</th>
                            <th>胜利</th>
                            <th>失败</th>
                            <th>平局</th>
                            <th>胜率</th>
                            <th>平局率</th>
                            <th>失败率</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    # 添加详细统计表格数据
    for row in vote_rows:
        win_rate = round(float(row['win_rate']), 2)
        tie_rate = round(float(row['tie_rate']), 2)
        loss_rate = round(float(row['loss_rate']), 2)
        html_content += f"""
                        <tr>
                            <td class="winner">{row['model']}</td>
                            <td>{row['total_battles']}</td>
                            <td class="winner">{row['wins']}</td>
                            <td class="loser">{row['losses']}</td>
                            <td class="tie">{row['ties']}</td>
                            <td class="winner">{win_rate:.2f}%</td>
                            <td class="tie">{tie_rate:.2f}%</td>
                            <td class="loser">{loss_rate:.2f}%</td>
                        </tr>"""
    
    html_content += f"""
                    </tbody>
                </table>
            </div>

            <div class="footer">
                <p>Report Generated: {timestamp} | Data Source: {data_source_text}</p>
                <p>ELO Rating System | K-Factor: 32 | Confidence Interval: 95%</p>
                <p>This report is automatically generated and supports scheduled updates</p>
            </div>
        </div>
    </div>

    <script>
        // 图表数据
        const voteDistributionData = {{
            leftvote: {distribution_data.get('leftvote', 0)},
            rightvote: {distribution_data.get('rightvote', 0)},
            tievote: {distribution_data.get('tievote', 0)}
        }};
        
        const modelData = {{
            labels: {[f'"{row["model"]}"' for row in vote_rows]},
            winRates: {[round(float(row['win_rate']), 2) for row in vote_rows]},
            barColors: {['rgba(40, 167, 69, 0.8)' if i == 0 else 'rgba(102, 126, 234, 0.8)' for i in range(len(vote_rows))]},
            borderColors: {['rgba(40, 167, 69, 1)' if i == 0 else 'rgba(102, 126, 234, 1)' for i in range(len(vote_rows))]}
        }};
        
        // 等待页面完全加载后初始化图表
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                initCharts();
            }}, 500);
        }});
        
        // 如果页面已经加载完成，立即初始化
        if (document.readyState === 'complete') {{
            setTimeout(function() {{
                initCharts();
            }}, 500);
        }}
        
        function initCharts() {{
            // 初始化投票分布饼图
            const pieCtx = document.getElementById('voteDistributionChart');
            if (pieCtx && typeof Chart !== 'undefined') {{
                new Chart(pieCtx, {{
                    type: 'pie',
                    data: {{
                        labels: ['Left Wins', 'Right Wins', 'Ties'],
                        datasets: [{{
                            data: [voteDistributionData.leftvote, voteDistributionData.rightvote, voteDistributionData.tievote],
                            backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                            borderColor: ['#1e7e34', '#bd2130', '#d39e00'],
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                position: 'bottom',
                                labels: {{
                                    color: '#fff',
                                    font: {{
                                        size: 14
                                    }}
                                }}
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                borderColor: '#fff',
                                borderWidth: 1
                            }}
                        }}
                    }}
                }});
            }}
            
            // 初始化模型胜率对比柱状图
            const barCtx = document.getElementById('modelWinRateChart');
            if (barCtx && typeof Chart !== 'undefined') {{
                new Chart(barCtx, {{
                    type: 'bar',
                    data: {{
                        labels: modelData.labels,
                        datasets: [{{
                            label: 'Win Rate (%)',
                            data: modelData.winRates,
                            backgroundColor: modelData.barColors,
                            borderColor: modelData.borderColors,
                            borderWidth: 2
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {{
                            legend: {{
                                display: false
                            }},
                            tooltip: {{
                                backgroundColor: 'rgba(0,0,0,0.8)',
                                titleColor: '#fff',
                                bodyColor: '#fff',
                                borderColor: '#fff',
                                borderWidth: 1
                            }}
                        }},
                        scales: {{
                            y: {{
                                beginAtZero: true,
                                max: 100,
                                ticks: {{
                                    color: '#fff',
                                    font: {{
                                        size: 12
                                    }},
                                    callback: function(value) {{
                                        return value + '%';
                                    }}
                                }},
                                grid: {{
                                    color: 'rgba(255,255,255,0.1)'
                                }}
                            }},
                            x: {{
                                ticks: {{
                                    color: '#fff',
                                    font: {{
                                        size: 12
                                    }}
                                }},
                                grid: {{
                                    color: 'rgba(255,255,255,0.1)'
                                }}
                            }}
                        }}
                    }}
                }});
            }}
        }}
    </script>
</body>
</html>"""
    
    # 保存HTML文件 - 直接使用固定文件名
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(t('report_generated').format('report.html'))
    return 'report.html'

def create_summary_report():
 
    print(t('summary_report'))
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open('vote_analysis.csv', 'r', encoding='utf-8') as f:
            vote_data = f.read()
        
        with open('elo_rankings.csv', 'r', encoding='utf-8') as f:
            elo_data = f.read()
            
        with open('vote_distribution.json', 'r', encoding='utf-8') as f:
            distribution_data = json.load(f)
    except FileNotFoundError as e:
        print(t('data_file_missing').format(e))
        return False
    
    # 解析数据
    vote_lines = vote_data.strip().split('\n')
    vote_headers = vote_lines[0].split(',')
    vote_rows = [dict(zip(vote_headers, line.split(','))) for line in vote_lines[1:]]
    
    elo_lines = elo_data.strip().split('\n')
    elo_headers = elo_lines[0].split(',')
    elo_rows = [dict(zip(elo_headers, line.split(','))) for line in elo_lines[1:]]
    
    # 生成摘要报告
    summary_content = "# FastChat 投票分析摘要报告\n\n"
    summary_content += f"## 报告信息\n- **生成时间**: {timestamp}\n- **分析工具**: FastChat 投票分析系统\n- **数据来源**: Arena 投票日志\n\n"
    summary_content += f"## 统计概览\n- **总投票数**: {distribution_data.get('leftvote', 0) + distribution_data.get('rightvote', 0) + distribution_data.get('tievote', 0) + distribution_data.get('bothbad_vote', 0)}\n- **参与模型数**: {len(vote_rows)}\n- **有效对战数**: {distribution_data.get('leftvote', 0) + distribution_data.get('rightvote', 0) + distribution_data.get('tievote', 0)}\n\n"
    summary_content += f"## 投票分布\n- **左方获胜**: {distribution_data.get('leftvote', 0)} 次\n- **右方获胜**: {distribution_data.get('rightvote', 0)} 次\n- **平局**: {distribution_data.get('tievote', 0)} 次\n\n"
    summary_content += "## ELO排名结果\n"
    for i, row in enumerate(elo_rows):
        rank = i + 1
        win_rate = round(float(row['win_rate']), 2)
        summary_content += f"### 第{rank}名: {row['model']}\n- **ELO评分**: {row['elo_rating']}\n- **总对战**: {row['total_battles']}\n- **胜利**: {row['wins']}\n- **失败**: {row['losses']}\n- **平局**: {row['ties']}\n- **胜率**: {win_rate:.2f}%%\n\n"
    summary_content += "## 详细统计\n\n| 模型名称 | 总对战 | 胜利 | 失败 | 平局 | 胜率 | 平局率 | 失败率 |\n|---------|--------|------|------|------|------|--------|--------|\n"
    for row in vote_rows:
        win_rate = round(float(row['win_rate']), 2)
        tie_rate = round(float(row['tie_rate']), 2)
        loss_rate = round(float(row['loss_rate']), 2)
        summary_content += f"| {row['model']} | {row['total_battles']} | {row['wins']} | {row['losses']} | {row['ties']} | {win_rate:.2f}%% | {tie_rate:.2f}%% | {loss_rate:.2f}%% |\n"
    summary_content += f"\n## 分析结论\n- 本次分析共处理了 {distribution_data.get('leftvote', 0) + distribution_data.get('rightvote', 0) + distribution_data.get('tievote', 0) + distribution_data.get('bothbad_vote', 0)} 场对战\n- 参与模型数量: {len(vote_rows)} 个\n- 分析时间: {timestamp}\n\n---\n*此报告由自动化脚本生成，支持定时任务更新*\n"
    
    # 保存摘要报告 - 直接使用固定文件名
    with open('summary.md', 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    print(t('summary_generated').format('summary.md'))
    return 'summary.md'

def cleanup_old_reports(keep_days=7):
   
    print(t('cleanup_old_reports').format(keep_days))
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 60 * 60)
    
    # 清理旧报告
    for pattern in ['report_*.html', 'summary_*.md']:
        for file_path in Path('.').glob(pattern):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    print(t('deleted_old_report').format(file_path))
                except Exception as e:
                    print(t('delete_failed').format(file_path, e))

def generate_vote_distribution_chart(distribution_data):
    """生成投票分布饼图并返回base64编码的图片"""
    try:
        # 设置中文字体和更大的字体大小
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 14  # 设置默认字体大小
        
        # 准备数据
        labels = ['Left Wins', 'Right Wins', 'Ties']
        sizes = [
            distribution_data.get('leftvote', 0),
            distribution_data.get('rightvote', 0), 
            distribution_data.get('tievote', 0)
        ]
        colors = ['#28a745', '#dc3545', '#ffc107']
        
        # 创建图表，增大图片尺寸，设置白色背景
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')  # 设置图片背景为白色
        fig.patch.set_alpha(1.0)
        ax.set_facecolor('white')  # 设置坐标轴背景为白色
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                         startangle=90, 
                                         textprops={'fontsize': 16, 'fontweight': 'bold', 'color': '#333333'},
                                         pctdistance=0.85)
        
        # 设置标题，使用深色文字
        ax.set_title('Vote Type Distribution', fontsize=20, fontweight='bold', pad=30, color='#333333')
        
        # 设置百分比文字样式
        for autotext in autotexts:
            autotext.set_color('white')  # 百分比文字保持白色，因为它们在彩色扇形内
            autotext.set_fontsize(16)
            autotext.set_fontweight('bold')
        
        # 设置标签文字样式为深色
        for text in texts:
            text.set_fontsize(16)
            text.set_fontweight('bold')
            text.set_color('#333333')
        
        # 确保饼图是圆形
        ax.axis('equal')
        
        # 转换为base64，使用白色背景
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=200, bbox_inches='tight', 
                   facecolor='white', edgecolor='none', transparent=False)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        
        return f'<img src="data:image/png;base64,{img_base64}" style="width:100%;max-width:600px;height:auto;">'
        
    except Exception as e:
        print(f"Error generating vote distribution chart: {e}")
        return '<p style="text-align:center;color:#666;">Chart generation failed</p>'

def generate_winrate_chart(vote_rows):
    """生成模型胜率对比柱状图并返回base64编码的图片"""
    try:
        # 设置中文字体和更大的字体大小
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['font.size'] = 14  # 设置默认字体大小
        
        # 准备数据
        labels = [row['model'] for row in vote_rows]
        win_rates = [round(float(row['win_rate']), 2) for row in vote_rows]
        colors = ['#28a745' if i == 0 else '#764ba2' for i in range(len(vote_rows))]
        
        # 创建图表，进一步增大图片尺寸，特别是高度，设置白色背景
        fig, ax = plt.subplots(figsize=(12, 10))  # 从(12,8)增加到(12,10)
        fig.patch.set_facecolor('white')  # 设置图片背景为白色
        fig.patch.set_alpha(1.0)
        ax.set_facecolor('white')  # 设置坐标轴背景为白色
        
        bars = ax.bar(labels, win_rates, color=colors, alpha=0.8, edgecolor='#333333', linewidth=2)
        
        # 进一步优化Y轴范围，让柱子看起来更高
        max_rate = max(win_rates)
        min_rate = min(win_rates)
        
        if max_rate < 30:
            # 极低胜率情况
            ax.set_ylim(0, max_rate + 10)
        elif max_rate < 50:
            # 低胜率情况，设置更紧凑的范围
            ax.set_ylim(0, max_rate + 8)
        elif max_rate < 70:
            # 中等胜率情况
            ax.set_ylim(0, max_rate + 6)
        elif max_rate < 90:
            # 高胜率情况
            ax.set_ylim(0, max_rate + 5)
        else:
            # 极高胜率情况
            ax.set_ylim(0, 105)
        
        # 设置样式，增大字体，使用深色文字
        ax.set_ylabel('Win Rate (%)', fontsize=18, fontweight='bold', color='#333333')  # 深色Y轴标签
        ax.set_title('Model Win Rate Comparison', fontsize=22, fontweight='bold', pad=35, color='#333333')  # 深色标题
        
        # 在柱子上显示数值，增大字体，动态调整位置，使用深色文字
        for bar, rate in zip(bars, win_rates):
            height = bar.get_height()
            # 根据柱子高度动态调整文字位置
            text_y = height + (ax.get_ylim()[1] * 0.015)  # 调整为1.5%
            ax.text(bar.get_x() + bar.get_width()/2., text_y,
                   f'{rate:.1f}%', ha='center', va='bottom', 
                   fontweight='bold', fontsize=18, color='#333333')  # 深色数值标签
        
        # 设置网格为浅灰色
        ax.grid(True, alpha=0.3, linestyle='--', color='#cccccc')
        ax.set_axisbelow(True)
        
        # 设置坐标轴标签字体大小和颜色
        ax.tick_params(axis='both', which='major', labelsize=16, colors='#333333')  # 深色刻度
        ax.tick_params(axis='x', rotation=45, colors='#333333')
        
        # 设置坐标轴颜色
        ax.spines['bottom'].set_color('#333333')
        ax.spines['top'].set_color('#333333')
        ax.spines['right'].set_color('#333333')
        ax.spines['left'].set_color('#333333')
        
        # 调整布局，进一步优化边距
        plt.xticks(rotation=45, ha='right', fontsize=16, fontweight='bold', color='#333333')  # 深色X轴标签
        plt.yticks(fontsize=16, color='#333333')  # 深色Y轴刻度
        plt.subplots_adjust(bottom=0.12, top=0.88, left=0.08, right=0.96)  # 进一步优化边距
        
        # 转换为base64，提高DPI，使用白色背景
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=200, bbox_inches='tight',
                   facecolor='white', edgecolor='none', transparent=False, pad_inches=0.05)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        
        return f'<img src="data:image/png;base64,{img_base64}" style="width:100%;max-width:600px;height:auto;">'
        
    except Exception as e:
        print(f"Error generating win rate chart: {e}")
        return '<p style="text-align:center;color:#666;">Chart generation failed</p>'

def create_archive_readme(archive_dir, reports_generated):
    """创建归档目录的README.txt文件"""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    readme_content = f"""FastChat Vote Analysis Archive Directory
==========================================

This directory contains a complete analysis archive for {timestamp} with the following files:

- vote_analysis.csv    : Vote statistics analysis results (wins/losses/win rates per model)
- elo_rankings.csv     : ELO ranking data (ELO scores and rankings per model)  
- vote_distribution.json: Vote distribution data (left/right/tie counts)
- report.html          : Visual HTML report for browser viewing
- summary.md           : Markdown summary report for email or documentation
- README.txt           : This description file

Notes:
1. All files are automatically generated for archival and future reference.
2. Open report.html directly in a browser to view the visual report.
3. summary.md is suitable for email, documentation, or knowledge base archival.
4. vote_analysis.csv/elo_rankings.csv/vote_distribution.json are raw analysis results for secondary analysis.

For batch archive management, manage the parent reports directory directly.
"""
    with open('README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)

def main():
    parser = argparse.ArgumentParser(description="FastChat 一键报告生成脚本")
    parser.add_argument("--log-file", type=str, default=None, 
                       help="投票日志文件路径，如果不指定将自动查找最新的日志文件")
    parser.add_argument("--html-only", action="store_true", 
                       help="只生成HTML报告")
    parser.add_argument("--summary-only", action="store_true", 
                       help="只生成摘要报告")
    parser.add_argument("--no-cleanup", action="store_true", 
                       help="不清理旧报告")
    parser.add_argument("--cleanup-days", type=int, default=30, 
                       help="清理多少天前的报告 (默认: 30天)")
    parser.add_argument("--cumulative", action="store_true",
                       help="分析累积的历史数据而不是单一日志文件")
    parser.add_argument("--force", action="store_true",
                       help="强制分析，即使数据没有变化")
    parser.add_argument("--check-only", action="store_true",
                       help="只检查日志文件状态，不生成报告")
    
    args = parser.parse_args()
    
    # 检查日志文件
    if not args.cumulative:
        if args.log_file is None:
            # 自动查找最新的日志文件
            print("🔍 未指定日志文件，正在自动查找最新的日志文件...")
            latest_log = find_latest_log_file()
            if latest_log is None:
                print("❌ 未找到任何日志文件 (*-conv.json)")
                print("💡 请确保FastChat正在运行并生成日志文件")
                sys.exit(1)
            args.log_file = str(latest_log)
            print(f"✅ 找到最新日志文件: {args.log_file}")
        
        if not Path(args.log_file).exists():
            print(t('log_file_not_found').format(args.log_file))
            print("💡 请确保FastChat正在运行并生成日志文件")
            sys.exit(1)
        
        log_file = Path(args.log_file).resolve()
        
        # 检查文件变化
        has_changes, last_mtime, last_size = check_log_file_changes(log_file)
        left_votes, right_votes, tie_votes, bothbad_votes, total_votes = count_vote_entries(log_file)
        
        # 显示日志文件状态
        print(f"\n📋 日志文件状态:")
        print(f"  📁 文件路径: {log_file}")
        print(f"  📊 投票统计: 左方获胜={left_votes}, 右方获胜={right_votes}, 平局={tie_votes}, 两个都不好={bothbad_votes}, 总计={total_votes}")
        print(f"  🕐 修改时间: {datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  📏 文件大小: {log_file.stat().st_size} bytes")
        
        if not has_changes and not args.force:
            print(f"\n⚠️  检测到日志文件自上次分析以来没有变化！")
            print(f"   上次分析时间: {datetime.fromtimestamp(last_mtime).strftime('%Y-%m-%d %H:%M:%S') if last_mtime else '未知'}")
            print(f"   上次文件大小: {last_size} bytes" if last_size else "")
            print(f"\n💡 如果您想要重新生成报告，请使用以下选项之一:")
            print(f"   1. 使用 --force 参数强制重新分析")
            print(f"   2. 使用 --cumulative 参数分析所有历史数据")
            print(f"   3. 等待新的投票数据生成")
            print(f"\n🔄 示例命令:")
            print(f"   python generate_report.py --force")
            print(f"   python generate_report.py --cumulative")
            
            if args.check_only:
                print(f"\n✅ 状态检查完成")
                sys.exit(0)
            else:
                print(f"\n❌ 跳过报告生成（数据无变化）")
                sys.exit(0)
        elif has_changes:
            print(f"\n✅ 检测到新数据，将生成新报告")
        elif args.force:
            print(f"\n🔄 强制模式：即使数据未变化也将重新生成报告")
        
        if args.check_only:
            print(f"\n✅ 状态检查完成")
            sys.exit(0)
            
    else:
        log_file = None  # 累积分析不需要单一日志文件
    
    # 创建时间戳
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    
    # 创建归档目录
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    archive_dir = reports_dir / timestamp
    archive_dir.mkdir(exist_ok=True)
    
    # 创建logs_archive目录
    logs_archive_dir = Path("logs_archive")
    logs_archive_dir.mkdir(exist_ok=True)
    
    # 生成 logs_archive/README.txt
    with open(logs_archive_dir / 'README.txt', 'w', encoding='utf-8') as f:
        f.write('''FastChat 日志归档目录
====================

本目录用于集中存放所有原始投票日志文件，便于统一管理和后续分析。

- 每个日志文件名如 2025-06-26-conv.json，表示当天的投票数据。
- 日志文件为JSON格式，记录了每一场对战的详细信息。
- 日志文件不会被覆盖，便于追溯和复查。

建议：如需长期归档，可定期备份本目录。
''')

    # 复制日志文件到归档目录
    if not args.cumulative:
        shutil.copy2(log_file, archive_dir / 'raw_log.json')
    
    # 计算static目录路径（在改变工作目录之前）
    static_reports_dir = Path(__file__).parent / "static" / "reports"
    static_reports_dir.mkdir(parents=True, exist_ok=True)
    
    # 切换到归档目录
    os.chdir(archive_dir)
    
    # 分析数据
    if args.cumulative:
        print(t('using_cumulative_analysis'))
        vote_rows, elo_rows, distribution_data = analyze_cumulative_vote_data()
        if not vote_rows or not elo_rows or not distribution_data:
            print(t('cumulative_analysis_failed'))
            sys.exit(1)
    else:
        # 在分析函数中设置强制模式
        analyze_vote_data._force_mode = args.force
        vote_rows, elo_rows, distribution_data = analyze_vote_data(log_file)
        if not vote_rows or not elo_rows or not distribution_data:
            print(t('data_analysis_failed'))
            sys.exit(1)
    
    # 生成报告
    reports_generated = []
    if not args.summary_only:
        html_report = create_report_html(log_file if not args.cumulative else "累积历史数据", vote_rows, elo_rows, distribution_data)
        if html_report:
            reports_generated.append('report.html')
    if not args.html_only:
        summary_report = create_summary_report()
        if summary_report:
            reports_generated.append('summary.md')
    
    # 创建归档说明文件
    create_archive_readme(archive_dir, reports_generated)
    
    # === 自动复制到 static/reports/ 目录 ===
    try:
        # 直接复制生成的报告文件
        actual_report_path = Path("report.html")
        if actual_report_path.exists():
            # 复制为最新报告
            shutil.copy2(actual_report_path, static_reports_dir / "report.html")
            print(t('copied_to_static'))
        else:
            print(t('report_not_found').format(actual_report_path.absolute()))
    except Exception as e:
        print(t('copy_failed').format(e))
    
    # 清理旧报告
    if not args.no_cleanup:
        cleanup_old_reports(args.cleanup_days)
    
    # 输出结果
    print("\n" + t('separator'))
    print(t('report_complete'))
    print(t('archive_dir').format(archive_dir.absolute()))
    print(t('generated_files'))
    for report in reports_generated:
        print(f"  - {archive_dir / report}")
    print(f"  - {archive_dir / 'vote_analysis.csv'}")
    print(f"  - {archive_dir / 'elo_rankings.csv'}")
    print(f"  - {archive_dir / 'vote_distribution.json'}")
    if not args.cumulative:
        print(f"  - {archive_dir / 'raw_log.json'}")
    print(f"  - {archive_dir / 'README.txt'}")
    if 'report.html' in reports_generated:
        print(f"\n{t('view_html_report').format(archive_dir / 'report.html')}")
    
    analysis_type = "累积历史数据分析" if args.cumulative else "单一日志文件分析"
    print(f"\n📊 分析类型: {analysis_type}")
    print(f"\n{t('next_run_time').format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
    print(t('crontab_tip'))

if __name__ == "__main__":
    main() 