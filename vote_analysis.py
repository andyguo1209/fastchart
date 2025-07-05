#!/usr/bin/env python3
"""
FastChat 投票统计工具
用于分析 Arena 模式的投票结果
"""

import json
import pandas as pd
from collections import defaultdict, Counter
from datetime import datetime
import argparse
import os

def load_vote_data(log_file):
    """加载投票数据"""
    votes = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if data.get('type') in ['leftvote', 'rightvote', 'tievote', 'bothbad_vote']:
                    votes.append(data)
            except json.JSONDecodeError:
                continue
    return votes

def analyze_votes(votes):
    """分析投票数据"""
    if not votes:
        print("没有找到投票数据")
        return
    
    # 统计基本信息
    total_votes = len(votes)
    vote_types = Counter(vote['type'] for vote in votes)
    
    print(f"=== 投票统计概览 ===")
    print(f"总投票数: {total_votes}")
    print(f"投票类型分布:")
    for vote_type, count in vote_types.items():
        percentage = (count / total_votes) * 100
        print(f"  {vote_type}: {count} ({percentage:.1f}%)")
    
    # 分析模型对战结果
    model_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0, 'total': 0})
    
    for vote in votes:
        if 'states' in vote and len(vote['states']) >= 2:
            model_a = vote['states'][0].get('model_name', 'Unknown')
            model_b = vote['states'][1].get('model_name', 'Unknown')
            vote_type = vote['type']
            
            # 统计每个模型的胜负
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
                model_stats[model_a]['ties'] += 1
                model_stats[model_b]['ties'] += 1
            
            model_stats[model_a]['total'] += 1
            model_stats[model_b]['total'] += 1
    
    # 计算胜率
    print(f"\n=== 模型表现统计 ===")
    model_performance = []
    for model, stats in model_stats.items():
        if stats['total'] > 0:
            win_rate = (stats['wins'] / stats['total']) * 100
            tie_rate = (stats['ties'] / stats['total']) * 100
            loss_rate = (stats['losses'] / stats['total']) * 100
            
            model_performance.append({
                'model': model,
                'total_battles': stats['total'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'ties': stats['ties'],
                'win_rate': win_rate,
                'tie_rate': tie_rate,
                'loss_rate': loss_rate
            })
    
    # 按胜率排序
    model_performance.sort(key=lambda x: x['win_rate'], reverse=True)
    
    print(f"{'模型名称':<20} {'总对战':<8} {'胜利':<6} {'失败':<6} {'平局':<6} {'胜率':<6} {'平局率':<6}")
    print("-" * 80)
    for perf in model_performance:
        print(f"{perf['model']:<20} {perf['total_battles']:<8} {perf['wins']:<6} {perf['losses']:<6} {perf['ties']:<6} {perf['win_rate']:<6.1f}% {perf['tie_rate']:<6.1f}%")
    
    # 时间分析
    print(f"\n=== 时间分析 ===")
    timestamps = [vote['tstamp'] for vote in votes]
    if timestamps:
        start_time = datetime.fromtimestamp(min(timestamps))
        end_time = datetime.fromtimestamp(max(timestamps))
        print(f"投票时间范围: {start_time} 到 {end_time}")
        
        # 按小时统计
        hourly_votes = defaultdict(int)
        for ts in timestamps:
            hour = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:00')
            hourly_votes[hour] += 1
        
        print(f"\n每小时投票数 (前10个最活跃时段):")
        sorted_hours = sorted(hourly_votes.items(), key=lambda x: x[1], reverse=True)
        for hour, count in sorted_hours[:10]:
            print(f"  {hour}: {count} 票")
    
    return model_performance

def export_to_csv(model_performance, output_file):
    """导出结果到CSV文件"""
    if model_performance:
        df = pd.DataFrame(model_performance)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n结果已导出到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='FastChat 投票统计工具')
    parser.add_argument('--log-file', type=str, default='logs/chat.log', 
                       help='投票日志文件路径')
    parser.add_argument('--output', type=str, default='vote_analysis.csv',
                       help='输出CSV文件路径')
    parser.add_argument('--export', action='store_true',
                       help='是否导出结果到CSV文件')
    
    args = parser.parse_args()
    
    # 检查日志文件是否存在
    if not os.path.exists(args.log_file):
        print(f"错误: 找不到日志文件 {args.log_file}")
        print("请确保FastChat正在运行并生成日志文件")
        return
    
    print(f"正在分析投票数据: {args.log_file}")
    votes = load_vote_data(args.log_file)
    model_performance = analyze_votes(votes)
    
    if args.export and model_performance:
        # 导出模型表现数据
        export_to_csv(model_performance, args.output)
        
        # 生成投票类型分布数据
        vote_types = Counter(vote['type'] for vote in votes)
        vote_distribution = {
            'leftvote': vote_types.get('leftvote', 0),
            'rightvote': vote_types.get('rightvote', 0),
            'tievote': vote_types.get('tievote', 0),
            'bothbad_vote': vote_types.get('bothbad_vote', 0)
        }
        
        with open('vote_distribution.json', 'w', encoding='utf-8') as f:
            json.dump(vote_distribution, f, ensure_ascii=False, indent=2)
        print(f"投票分布数据已导出到: vote_distribution.json")

if __name__ == "__main__":
    main() 