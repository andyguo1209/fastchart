#!/usr/bin/env python3
"""
FastChat 投票数据库管理器
支持增量更新和实时数据查询
"""

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
import hashlib

class VoteDatabase:
    def __init__(self, db_path="votes.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建投票记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vote_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                model_a TEXT NOT NULL,
                model_b TEXT NOT NULL,
                winner TEXT,
                conversation_data TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建模型统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_stats (
                model_name TEXT PRIMARY KEY,
                total_battles INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,
                elo_rating REAL DEFAULT 1000.0,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建日志文件处理记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processed_logs (
                file_path TEXT PRIMARY KEY,
                file_hash TEXT NOT NULL,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                record_count INTEGER DEFAULT 0
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_timestamp ON votes(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_type ON votes(vote_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_models ON votes(model_a, model_b)')
        
        conn.commit()
        conn.close()
    
    def get_file_hash(self, file_path):
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def is_file_processed(self, file_path):
        """检查文件是否已经处理过"""
        if not os.path.exists(file_path):
            return False
            
        current_hash = self.get_file_hash(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_hash FROM processed_logs WHERE file_path = ?', (file_path,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result is None:
            return False
        
        return result[0] == current_hash
    
    def mark_file_processed(self, file_path, record_count):
        """标记文件为已处理"""
        file_hash = self.get_file_hash(file_path)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processed_logs (file_path, file_hash, processed_at, record_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, ?)
        ''', (file_path, file_hash, record_count))
        
        conn.commit()
        conn.close()
    
    def load_votes_from_log(self, log_file_path):
        """从日志文件加载投票数据到数据库"""
        if self.is_file_processed(log_file_path):
            print(f"📋 文件已处理过，跳过: {log_file_path}")
            return 0
        
        print(f"📥 正在处理新日志文件: {log_file_path}")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        new_records = 0
        
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        
                        # 只处理投票类型的记录
                        if data.get('type') not in ['leftvote', 'rightvote', 'tievote', 'bothbad_vote']:
                            continue
                        
                        # 检查是否有足够的模型状态
                        states = data.get('states', [])
                        if len(states) < 2:
                            continue
                        
                        # 提取模型名称
                        model_a = states[0].get('model_name', '')
                        model_b = states[1].get('model_name', '')
                        
                        if not model_a or not model_b:
                            continue
                        
                        # 生成唯一的投票ID
                        vote_id = hashlib.md5(f"{log_file_path}:{line_num}:{data.get('tstamp', '')}".encode()).hexdigest()
                        
                        # 确定获胜者
                        vote_type = data.get('type')
                        winner = None
                        if vote_type == 'leftvote':
                            winner = model_a
                        elif vote_type == 'rightvote':
                            winner = model_b
                        elif vote_type == 'tievote':
                            winner = 'tie'
                        elif vote_type == 'bothbad_vote':
                            winner = 'both_bad'
                        
                        # 插入投票记录
                        cursor.execute('''
                            INSERT OR IGNORE INTO votes 
                            (vote_id, timestamp, vote_type, model_a, model_b, winner, conversation_data)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (vote_id, data.get('tstamp', ''), vote_type, model_a, model_b, winner, json.dumps(data)))
                        
                        if cursor.rowcount > 0:
                            new_records += 1
                            
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"⚠️ 处理第{line_num}行时出错: {e}")
                        continue
            
            conn.commit()
            self.mark_file_processed(log_file_path, new_records)
            print(f"✅ 成功处理 {new_records} 条新记录")
            
        except Exception as e:
            print(f"❌ 处理日志文件失败: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return new_records
    
    def update_model_stats(self):
        """更新模型统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 获取所有模型
            cursor.execute('SELECT DISTINCT model_a FROM votes UNION SELECT DISTINCT model_b FROM votes')
            models = [row[0] for row in cursor.fetchall()]
            
            for model in models:
                # 计算统计数据
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_battles,
                        SUM(CASE WHEN winner = ? THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN winner != ? AND winner != 'tie' AND winner != 'both_bad' THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN winner = 'tie' THEN 1 ELSE 0 END) as ties
                    FROM votes 
                    WHERE (model_a = ? OR model_b = ?) AND vote_type IN ('leftvote', 'rightvote', 'tievote')
                ''', (model, model, model, model))
                
                result = cursor.fetchone()
                total_battles, wins, losses, ties = result
                
                # 更新模型统计
                cursor.execute('''
                    INSERT OR REPLACE INTO model_stats 
                    (model_name, total_battles, wins, losses, ties, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (model, total_battles, wins, losses, ties))
            
            conn.commit()
            print(f"✅ 已更新 {len(models)} 个模型的统计数据")
            
        except Exception as e:
            print(f"❌ 更新模型统计失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def calculate_elo_ratings(self, k_factor=32):
        """计算ELO评级"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 重置所有模型的ELO评级为1000
            cursor.execute('UPDATE model_stats SET elo_rating = 1000.0')
            
            # 按时间顺序获取所有有效对战
            cursor.execute('''
                SELECT model_a, model_b, winner, timestamp 
                FROM votes 
                WHERE vote_type IN ('leftvote', 'rightvote', 'tievote')
                ORDER BY timestamp
            ''')
            
            battles = cursor.fetchall()
            
            for model_a, model_b, winner, timestamp in battles:
                # 获取当前ELO评级
                cursor.execute('SELECT elo_rating FROM model_stats WHERE model_name = ?', (model_a,))
                elo_a = cursor.fetchone()[0]
                
                cursor.execute('SELECT elo_rating FROM model_stats WHERE model_name = ?', (model_b,))
                elo_b = cursor.fetchone()[0]
                
                # 计算期望得分
                expected_a = 1 / (1 + 10 ** ((elo_b - elo_a) / 400))
                expected_b = 1 / (1 + 10 ** ((elo_a - elo_b) / 400))
                
                # 确定实际得分
                if winner == model_a:
                    score_a, score_b = 1, 0
                elif winner == model_b:
                    score_a, score_b = 0, 1
                elif winner == 'tie':
                    score_a, score_b = 0.5, 0.5
                else:
                    continue  # 跳过both_bad
                
                # 更新ELO评级
                new_elo_a = elo_a + k_factor * (score_a - expected_a)
                new_elo_b = elo_b + k_factor * (score_b - expected_b)
                
                cursor.execute('UPDATE model_stats SET elo_rating = ? WHERE model_name = ?', (new_elo_a, model_a))
                cursor.execute('UPDATE model_stats SET elo_rating = ? WHERE model_name = ?', (new_elo_b, model_b))
            
            conn.commit()
            print(f"✅ 已计算 {len(battles)} 场对战的ELO评级")
            
        except Exception as e:
            print(f"❌ 计算ELO评级失败: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_vote_distribution(self):
        """获取投票分布统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vote_type, COUNT(*) 
            FROM votes 
            GROUP BY vote_type
        ''')
        
        result = {}
        for vote_type, count in cursor.fetchall():
            result[vote_type] = count
        
        conn.close()
        return result
    
    def get_model_rankings(self):
        """获取模型排名"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT model_name, total_battles, wins, losses, ties, elo_rating,
                   CASE WHEN total_battles > 0 THEN (wins * 100.0 / total_battles) ELSE 0 END as win_rate,
                   CASE WHEN total_battles > 0 THEN (ties * 100.0 / total_battles) ELSE 0 END as tie_rate,
                   CASE WHEN total_battles > 0 THEN (losses * 100.0 / total_battles) ELSE 0 END as loss_rate
            FROM model_stats 
            WHERE total_battles > 0
            ORDER BY elo_rating DESC
        ''')
        
        rankings = []
        for row in cursor.fetchall():
            rankings.append({
                'model': row[0],
                'total_battles': row[1],
                'wins': row[2],
                'losses': row[3],
                'ties': row[4],
                'elo_rating': round(row[5], 1),
                'win_rate': round(row[6], 1),
                'tie_rate': round(row[7], 1),
                'loss_rate': round(row[8], 1)
            })
        
        conn.close()
        return rankings
    
    def sync_from_logs(self, log_dir="."):
        """同步所有日志文件"""
        log_files = list(Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs_archive')).glob("*-conv.json"))
        
        if not log_files:
            print("❌ 未找到任何日志文件")
            return
        
        print(f"🔍 找到 {len(log_files)} 个日志文件")
        
        total_new_records = 0
        for log_file in sorted(log_files):
            new_records = self.load_votes_from_log(str(log_file))
            total_new_records += new_records
        
        if total_new_records > 0:
            print(f"📊 正在更新统计数据...")
            self.update_model_stats()
            self.calculate_elo_ratings()
            print(f"✅ 同步完成，共处理 {total_new_records} 条新记录")
        else:
            print("📋 没有新数据需要处理")
    
    def get_database_stats(self):
        """获取数据库统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM votes')
        total_votes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM model_stats WHERE total_battles > 0')
        active_models = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM processed_logs')
        processed_files = cursor.fetchone()[0]
        
        cursor.execute('SELECT MAX(created_at) FROM votes')
        last_vote = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_votes': total_votes,
            'active_models': active_models,
            'processed_files': processed_files,
            'last_vote': last_vote
        }

if __name__ == "__main__":
    # 示例用法
    db = VoteDatabase()
    
    print("🚀 FastChat 投票数据库管理器")
    print("=" * 50)
    
    # 同步日志文件
    db.sync_from_logs()
    
    # 显示数据库统计
    stats = db.get_database_stats()
    print(f"\n📊 数据库统计:")
    print(f"  总投票数: {stats['total_votes']}")
    print(f"  活跃模型: {stats['active_models']}")
    print(f"  已处理文件: {stats['processed_files']}")
    print(f"  最后投票: {stats['last_vote']}")
    
    # 显示排名
    rankings = db.get_model_rankings()
    print(f"\n🏆 模型排名:")
    for i, model in enumerate(rankings, 1):
        print(f"  {i}. {model['model']}: ELO {model['elo_rating']}, 胜率 {model['win_rate']:.1f}%") 