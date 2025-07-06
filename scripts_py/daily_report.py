#!/usr/bin/env python3
"""
FastChat 当天数据统计脚本
专门用于统计当天的投票数据，生成简化的报告
"""

import json
import os
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import argparse

def get_today_log_file():
    """获取当天的日志文件"""
    today = datetime.now().strftime('%Y-%m-%d')
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs_archive')
    log_file = os.path.join(log_dir, f"{today}-conv.json")
    if os.path.exists(log_file):
        return log_file
    else:
        print(f"❌ 未找到当天日志文件: {log_file}")
        return None

def analyze_daily_data(log_file):
    """分析当天的数据"""
    if not log_file:
        return None
        
    print(f"📊 分析当天数据: {log_file}")
    
    # 统计数据
    vote_counts = defaultdict(int)
    model_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0, 'total': 0})
    conversation_count = 0
    vote_count = 0
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    
                    # 统计对话数量
                    if data.get('type') == 'chat':
                        conversation_count += 1
                    
                    # 统计投票数据
                    elif data.get('type') in ['leftvote', 'rightvote', 'tievote', 'bothbad_vote']:
                        vote_count += 1
                        vote_type = data.get('type')
                        vote_counts[vote_type] += 1
                        
                        # 获取模型信息
                        states = data.get('states', [])
                        if len(states) >= 2:
                            model_a = states[0].get('model_name', 'Unknown')
                            model_b = states[1].get('model_name', 'Unknown')
                            
                            # 统计胜负
                            if vote_type == 'leftvote':
                                model_stats[model_a]['wins'] += 1
                                model_stats[model_b]['losses'] += 1
                            elif vote_type == 'rightvote':
                                model_stats[model_b]['wins'] += 1
                                model_stats[model_a]['losses'] += 1
                            elif vote_type == 'tievote':
                                model_stats[model_a]['ties'] += 1
                                model_stats[model_b]['ties'] += 1
                            elif vote_type == 'bothbad_vote':
                                # 双败不计入胜负，但计入总数
                                pass
                            
                            # 更新总数
                            model_stats[model_a]['total'] += 1
                            model_stats[model_b]['total'] += 1
                            
                except json.JSONDecodeError:
                    continue
                    
    except FileNotFoundError:
        print(f"❌ 文件不存在: {log_file}")
        return None
    
    # 计算胜率
    for model in model_stats:
        stats = model_stats[model]
        if stats['total'] > 0:
            stats['win_rate'] = (stats['wins'] / stats['total']) * 100
            stats['tie_rate'] = (stats['ties'] / stats['total']) * 100
            stats['loss_rate'] = (stats['losses'] / stats['total']) * 100
        else:
            stats['win_rate'] = stats['tie_rate'] = stats['loss_rate'] = 0
    
    return {
        'log_file': log_file,
        'conversation_count': conversation_count,
        'vote_count': vote_count,
        'vote_counts': dict(vote_counts),
        'model_stats': dict(model_stats),
        'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def generate_daily_report(data):
    """生成当天数据报告"""
    if not data:
        return None
        
    report = []
    report.append("# FastChat 当天数据统计报告")
    report.append(f"## 分析时间: {data['analysis_time']}")
    report.append(f"## 数据来源: {data['log_file']}")
    report.append("")
    
    # 基本统计
    report.append("## 📊 基本统计")
    report.append(f"- **对话总数**: {data['conversation_count']}")
    report.append(f"- **投票总数**: {data['vote_count']}")
    report.append(f"- **参与模型数**: {len(data['model_stats'])}")
    report.append("")
    
    # 投票分布
    report.append("## 🗳️ 投票分布")
    vote_counts = data['vote_counts']
    report.append(f"- **左方获胜**: {vote_counts.get('leftvote', 0)} 票")
    report.append(f"- **右方获胜**: {vote_counts.get('rightvote', 0)} 票")
    report.append(f"- **平局**: {vote_counts.get('tievote', 0)} 票")
    report.append(f"- **双败**: {vote_counts.get('bothbad_vote', 0)} 票")
    report.append("")
    
    # 模型统计
    report.append("## 🤖 模型统计")
    model_stats = data['model_stats']
    
    if model_stats:
        # 按胜率排序
        sorted_models = sorted(model_stats.items(), 
                             key=lambda x: x[1]['win_rate'], 
                             reverse=True)
        
        report.append("| 模型名称 | 总对战 | 胜利 | 失败 | 平局 | 胜率 |")
        report.append("|---------|--------|------|------|------|------|")
        
        for model, stats in sorted_models:
            report.append(f"| {model} | {stats['total']} | {stats['wins']} | {stats['losses']} | {stats['ties']} | {stats['win_rate']:.1f}% |")
    else:
        report.append("暂无模型对战数据")
    
    report.append("")
    
    # 数据洞察
    report.append("## 💡 数据洞察")
    if data['vote_count'] > 0:
        total_effective_votes = vote_counts.get('leftvote', 0) + vote_counts.get('rightvote', 0)
        if total_effective_votes > 0:
            left_win_rate = (vote_counts.get('leftvote', 0) / total_effective_votes) * 100
            report.append(f"- 左方模型胜率: {left_win_rate:.1f}%")
            report.append(f"- 右方模型胜率: {100 - left_win_rate:.1f}%")
        
        tie_rate = (vote_counts.get('tievote', 0) / data['vote_count']) * 100
        report.append(f"- 平局率: {tie_rate:.1f}%")
        
        if vote_counts.get('bothbad_vote', 0) > 0:
            bothbad_rate = (vote_counts.get('bothbad_vote', 0) / data['vote_count']) * 100
            report.append(f"- 双败率: {bothbad_rate:.1f}%")
    else:
        report.append("- 当天暂无投票数据")
    
    report.append("")
    report.append("---")
    report.append("*此报告由 daily_report.py 自动生成*")
    
    return "\n".join(report)

def save_report(report_content, output_file=None):
    """保存报告到文件"""
    if not output_file:
        today = datetime.now().strftime('%Y-%m-%d')
        output_file = f"daily_report_{today}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ 当天数据报告已保存: {output_file}")
    return output_file

def print_summary(data):
    """打印简要统计信息"""
    if not data:
        print("❌ 无数据可显示")
        return
    
    print("\n" + "="*50)
    print("📊 FastChat 当天数据统计")
    print("="*50)
    print(f"📁 数据文件: {data['log_file']}")
    print(f"🕐 分析时间: {data['analysis_time']}")
    print(f"💬 对话总数: {data['conversation_count']}")
    print(f"🗳️  投票总数: {data['vote_count']}")
    print(f"🤖 参与模型: {len(data['model_stats'])}")
    
    if data['vote_count'] > 0:
        print("\n📈 投票分布:")
        vote_counts = data['vote_counts']
        print(f"  左方获胜: {vote_counts.get('leftvote', 0)} 票")
        print(f"  右方获胜: {vote_counts.get('rightvote', 0)} 票")
        print(f"  平局: {vote_counts.get('tievote', 0)} 票")
        print(f"  双败: {vote_counts.get('bothbad_vote', 0)} 票")
        
        if data['model_stats']:
            print("\n🏆 模型排名:")
            sorted_models = sorted(data['model_stats'].items(), 
                                 key=lambda x: x[1]['win_rate'], 
                                 reverse=True)
            
            for i, (model, stats) in enumerate(sorted_models, 1):
                print(f"  {i}. {model}: {stats['wins']}胜 {stats['losses']}负 {stats['ties']}平 (胜率: {stats['win_rate']:.1f}%)")
    else:
        print("\n⚠️  当天暂无投票数据")
    
    print("="*50)

def main():
    parser = argparse.ArgumentParser(description="FastChat 当天数据统计")
    parser.add_argument("--log-file", help="指定日志文件路径（默认自动检测当天文件）")
    parser.add_argument("--output", help="输出报告文件路径")
    parser.add_argument("--no-save", action="store_true", help="不保存报告文件，仅显示统计")
    
    args = parser.parse_args()
    
    # 获取日志文件
    log_file = args.log_file or get_today_log_file()
    
    if not log_file:
        print("❌ 未找到可分析的日志文件")
        return
    
    # 分析数据
    data = analyze_daily_data(log_file)
    
    if not data:
        print("❌ 数据分析失败")
        return
    
    # 显示统计信息
    print_summary(data)
    
    # 生成和保存报告
    if not args.no_save:
        report_content = generate_daily_report(data)
        if report_content:
            save_report(report_content, args.output)

if __name__ == "__main__":
    main() 