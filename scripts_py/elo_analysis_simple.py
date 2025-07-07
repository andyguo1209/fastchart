#!/usr/bin/env python3
"""
FastChat ELO评分分析工具
基于投票数据计算模型的ELO评分和排名
"""

import json
import pandas as pd
import numpy as np
from collections import defaultdict
import argparse
import os
from pathlib import Path

class ELOCalculator:
    def __init__(self, k_factor=32, initial_rating=1000):
        self.k_factor = k_factor
        self.initial_rating = initial_rating
        self.ratings = defaultdict(lambda: initial_rating)
    
    def expected_score(self, rating_a, rating_b):
        """计算期望得分"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, rating_a, rating_b, score_a):
        """更新ELO评分"""
        expected_a = self.expected_score(rating_a, rating_b)
        expected_b = self.expected_score(rating_b, rating_a)
        
        new_rating_a = rating_a + self.k_factor * (score_a - expected_a)
        new_rating_b = rating_b + self.k_factor * ((1 - score_a) - expected_b)
        
        return new_rating_a, new_rating_b
    
    def process_battle(self, model_a, model_b, winner):
        """处理一场对战"""
        rating_a = self.ratings[model_a]
        rating_b = self.ratings[model_b]
        
        if winner == 'model_a':
            score_a = 1.0
        elif winner == 'model_b':
            score_a = 0.0
        else:  # tie
            score_a = 0.5
        
        new_rating_a, new_rating_b = self.update_ratings(rating_a, rating_b, score_a)
        self.ratings[model_a] = new_rating_a
        self.ratings[model_b] = new_rating_b
    
    def get_rankings(self):
        """获取排名"""
        sorted_models = sorted(self.ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_models

def load_battle_data(log_file):
    """加载对战数据"""
    battles = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                if data.get('type') in ['leftvote', 'rightvote', 'tievote', 'bothbad_vote']:
                    if 'states' in data and len(data['states']) >= 2:
                        model_a = data['states'][0].get('model_name', 'Unknown')
                        model_b = data['states'][1].get('model_name', 'Unknown')
                        
                        # 确定获胜者
                        if data['type'] == 'leftvote':
                            winner = 'model_a'
                        elif data['type'] == 'rightvote':
                            winner = 'model_b'
                        else:  # tievote or bothbad_vote
                            winner = 'tie'
                        
                        battles.append({
                            'model_a': model_a,
                            'model_b': model_b,
                            'winner': winner,
                            'timestamp': data.get('tstamp', 0)
                        })
            except json.JSONDecodeError:
                continue
    return battles

def analyze_elo_rankings(battles, k_factor=32):
    """分析ELO排名"""
    if not battles:
        print("没有找到对战数据")
        return None
    
    # 初始化ELO计算器
    elo_calc = ELOCalculator(k_factor=k_factor)
    
    # 按时间排序处理对战
    battles_sorted = sorted(battles, key=lambda x: x['timestamp'])
    
    print(f"正在处理 {len(battles_sorted)} 场对战...")
    
    # 处理每场对战
    for battle in battles_sorted:
        elo_calc.process_battle(
            battle['model_a'], 
            battle['model_b'], 
            battle['winner']
        )
    
    # 获取最终排名
    rankings = elo_calc.get_rankings()
    
    # 统计每个模型的对战次数
    battle_counts = defaultdict(int)
    for battle in battles:
        battle_counts[battle['model_a']] += 1
        battle_counts[battle['model_b']] += 1
    
    # 计算胜率统计
    win_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'ties': 0})
    for battle in battles:
        if battle['winner'] == 'model_a':
            win_stats[battle['model_a']]['wins'] += 1
            win_stats[battle['model_b']]['losses'] += 1
        elif battle['winner'] == 'model_b':
            win_stats[battle['model_b']]['wins'] += 1
            win_stats[battle['model_a']]['losses'] += 1
        else:  # tie
            win_stats[battle['model_a']]['ties'] += 1
            win_stats[battle['model_b']]['ties'] += 1
    
    # 生成结果
    results = []
    for rank, (model, elo_rating) in enumerate(rankings, 1):
        stats = win_stats[model]
        total_battles = battle_counts[model]
        win_rate = (stats['wins'] / total_battles * 100) if total_battles > 0 else 0
        
        results.append({
            'rank': rank,
            'model': model,
            'elo_rating': round(elo_rating, 1),
            'total_battles': total_battles,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'ties': stats['ties'],
            'win_rate': round(win_rate, 1)
        })
    
    return results

def print_results(results):
    """打印结果"""
    if not results:
        return
    
    print(f"\n=== ELO排名结果 ===")
    print(f"{'排名':<4} {'模型名称':<20} {'ELO评分':<8} {'总对战':<6} {'胜利':<4} {'失败':<4} {'平局':<4} {'胜率':<6}")
    print("-" * 70)
    
    for result in results:
        print(f"{result['rank']:<4} {result['model']:<20} {result['elo_rating']:<8} "
              f"{result['total_battles']:<6} {result['wins']:<4} {result['losses']:<4} "
              f"{result['ties']:<4} {result['win_rate']:<6.1f}%")

def export_results(results, output_file):
    """导出结果到CSV"""
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n结果已导出到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='FastChat ELO评分分析工具')
    parser.add_argument('--log-file', type=str, default='logs/chat.log',
                       help='投票日志文件路径')
    parser.add_argument('--output', type=str, default='elo_rankings.csv',
                       help='输出CSV文件路径')
    parser.add_argument('--k-factor', type=float, default=32,
                       help='ELO K因子 (默认: 32)')
    parser.add_argument('--export', action='store_true',
                       help='是否导出结果到CSV文件')
    
    args = parser.parse_args()
    
    # 检查日志文件
    if not os.path.exists(args.log_file):
        print(f"错误: 找不到日志文件 {args.log_file}")
        return
    
    print(f"正在分析ELO评分: {args.log_file}")
    print(f"K因子: {args.k_factor}")
    
    # 加载数据
    battles = load_battle_data(args.log_file)
    results = analyze_elo_rankings(battles, args.k_factor)
    
    if results:
        print_results(results)
        
        if args.export:
            # 创建 static/reports 目录
            reports_dir = Path(__file__).parent.parent / 'static' / 'reports'
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # 导出结果到 static/reports 目录
            output_path = reports_dir / args.output
            export_results(results, output_path)
    else:
        print("没有找到有效的对战数据")

if __name__ == "__main__":
    main() 