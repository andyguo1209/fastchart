#!/usr/bin/env python3
"""
FastChat 投票分析自动化脚本
自动分析投票数据，生成ELO排名，并启动Web展示
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

def run_command(cmd, description):
    """运行命令并处理错误"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} 完成")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None

def analyze_vote_data(log_file):
    """分析投票数据"""
    print(f"\n📊 开始分析投票数据: {log_file}")
    
    # 运行投票分析
    cmd = f"python vote_analysis.py --log-file {log_file} --export"
    output = run_command(cmd, "投票统计分析")
    
    # 运行ELO分析
    cmd = f"python elo_analysis_simple.py --log-file {log_file} --export"
    output = run_command(cmd, "ELO排名分析")
    
    return output is not None

def create_web_dashboard():
    """创建Web展示页面"""
    print("\n🌐 创建Web展示页面...")
    
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FastChat 投票分析仪表板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }
        .stat-label {
            color: #666;
            font-size: 1.1em;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .chart-title {
            text-align: center;
            margin-bottom: 20px;
            color: #333;
            font-size: 1.3em;
            font-weight: 600;
        }
        .table-container {
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        .table-title {
            text-align: center;
            margin-bottom: 20px;
            color: #333;
            font-size: 1.3em;
            font-weight: 600;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: #333;
            font-size: 1.1em;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .winner {
            color: #28a745;
            font-weight: bold;
        }
        .loser {
            color: #dc3545;
        }
        .tie {
            color: #ffc107;
            font-weight: bold;
        }
        .footer {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            text-align: center;
            color: white;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            margin: 10px;
            transition: all 0.3s ease;
        }
        .refresh-btn:hover {
            background: #5a6fd8;
            transform: translateY(-2px);
        }
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 FastChat 投票分析仪表板</h1>
            <p>模型对战结果统计与ELO排名分析</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
        </div>
        
        <div class="content">
            <!-- 统计概览 -->
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="totalVotes">-</div>
                    <div class="stat-label">总投票数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="totalBattles">-</div>
                    <div class="stat-label">总对战数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="totalModels">-</div>
                    <div class="stat-label">参与模型数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="timeRange">-</div>
                    <div class="stat-label">投票时间跨度</div>
                </div>
            </div>

            <!-- 图表区域 -->
            <div class="charts-grid">
                <div class="chart-container">
                    <div class="chart-title">📊 投票类型分布</div>
                    <canvas id="voteTypeChart" width="400" height="300"></canvas>
                </div>
                <div class="chart-container">
                    <div class="chart-title">🏆 模型胜率对比</div>
                    <canvas id="winRateChart" width="400" height="300"></canvas>
                </div>
            </div>

            <!-- ELO排名表格 -->
            <div class="table-container">
                <div class="chart-title">🏅 ELO排名表</div>
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
                    <tbody id="eloTableBody">
                        <!-- 数据将通过JavaScript动态加载 -->
                    </tbody>
                </table>
            </div>

            <!-- 详细统计表格 -->
            <div class="table-container">
                <div class="chart-title">📈 详细统计表</div>
                <table id="statsTable">
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
                    <tbody id="statsTableBody">
                        <!-- 数据将通过JavaScript动态加载 -->
                    </tbody>
                </table>
            </div>
        </div>

        <div class="footer">
            <p>🕒 最后更新时间: <span id="lastUpdate">-</span></p>
            <p>📊 数据来源: FastChat Arena 投票系统</p>
        </div>
    </div>

    <script>
        // 加载CSV数据并更新页面
        async function loadData() {
            try {
                // 加载ELO排名数据
                const eloResponse = await fetch('elo_rankings.csv');
                const eloText = await eloResponse.text();
                const eloData = parseCSV(eloText);
                
                // 加载投票统计数据
                const statsResponse = await fetch('vote_analysis.csv');
                const statsText = await statsResponse.text();
                const statsData = parseCSV(statsText);
                
                updateDashboard(eloData, statsData);
            } catch (error) {
                console.error('加载数据失败:', error);
                document.body.innerHTML = '<div style="text-align: center; color: white; padding: 50px;"><h2>❌ 数据加载失败</h2><p>请确保CSV文件存在且可访问</p></div>';
            }
        }

        function parseCSV(csvText) {
            const lines = csvText.trim().split('\\n');
            const headers = lines[0].split(',');
            const data = [];
            
            for (let i = 1; i < lines.length; i++) {
                const values = lines[i].split(',');
                const row = {};
                headers.forEach((header, index) => {
                    row[header.trim()] = values[index] ? values[index].trim() : '';
                });
                data.push(row);
            }
            
            return data;
        }

        function updateDashboard(eloData, statsData) {
            // 更新统计概览
            const totalVotes = statsData.reduce((sum, row) => sum + parseInt(row.total_battles), 0);
            const totalModels = statsData.length;
            
            document.getElementById('totalVotes').textContent = totalVotes;
            document.getElementById('totalBattles').textContent = totalVotes;
            document.getElementById('totalModels').textContent = totalModels;
            document.getElementById('timeRange').textContent = '实时更新';
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString('zh-CN');

            // 更新ELO表格
            const eloTableBody = document.getElementById('eloTableBody');
            eloTableBody.innerHTML = '';
            
            eloData.forEach((row, index) => {
                const tr = document.createElement('tr');
                const rank = index + 1;
                const isWinner = rank === 1;
                
                tr.innerHTML = `
                    <td>${rank}</td>
                    <td class="${isWinner ? 'winner' : ''}">${row.model}</td>
                    <td class="${isWinner ? 'winner' : ''}">${parseFloat(row.elo_rating).toFixed(1)}</td>
                    <td>${row.total_battles}</td>
                    <td class="winner">${row.wins}</td>
                    <td class="loser">${row.losses}</td>
                    <td class="tie">${row.ties}</td>
                    <td class="${isWinner ? 'winner' : ''}">${row.win_rate}%</td>
                `;
                eloTableBody.appendChild(tr);
            });

            // 更新统计表格
            const statsTableBody = document.getElementById('statsTableBody');
            statsTableBody.innerHTML = '';
            
            statsData.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.model}</td>
                    <td>${row.total_battles}</td>
                    <td class="winner">${row.wins}</td>
                    <td class="loser">${row.losses}</td>
                    <td class="tie">${row.ties}</td>
                    <td class="winner">${row.win_rate}%</td>
                    <td class="tie">${row.tie_rate}%</td>
                    <td class="loser">${row.loss_rate}%</td>
                `;
                statsTableBody.appendChild(tr);
            });

            // 创建图表
            createCharts(eloData, statsData);
        }

        function createCharts(eloData, statsData) {
            // 投票类型分布图表
            const voteTypeCtx = document.getElementById('voteTypeChart').getContext('2d');
            new Chart(voteTypeCtx, {
                type: 'doughnut',
                data: {
                    labels: ['左方获胜', '右方获胜', '平局'],
                    datasets: [{
                        data: [3, 1, 1], // 这里可以根据实际数据调整
                        backgroundColor: [
                            '#28a745',
                            '#dc3545',
                            '#ffc107'
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 20,
                                usePointStyle: true
                            }
                        }
                    }
                }
            });

            // 模型胜率对比图表
            const winRateCtx = document.getElementById('winRateChart').getContext('2d');
            new Chart(winRateCtx, {
                type: 'bar',
                data: {
                    labels: statsData.map(row => row.model),
                    datasets: [{
                        label: '胜率 (%)',
                        data: statsData.map(row => parseFloat(row.win_rate)),
                        backgroundColor: statsData.map((_, index) => 
                            index === 0 ? 'rgba(40, 167, 69, 0.8)' : 'rgba(220, 53, 69, 0.8)'
                        ),
                        borderColor: statsData.map((_, index) => 
                            index === 0 ? 'rgba(40, 167, 69, 1)' : 'rgba(220, 53, 69, 1)'
                        ),
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }

        // 页面加载时执行
        document.addEventListener('DOMContentLoaded', loadData);
        
        // 每30秒自动刷新一次
        setInterval(loadData, 30000);
    </script>
</body>
</html>"""
    
    with open('web_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ Web展示页面创建完成: web_dashboard.html")

def start_web_server(port=8080):
    """启动Web服务器"""
    print(f"\n🌐 启动Web服务器 (端口: {port})...")
    
    try:
        # 使用Python内置的HTTP服务器
        cmd = f"python -m http.server {port}"
        print(f"🚀 服务器启动命令: {cmd}")
        print(f"📱 请在浏览器中访问: http://localhost:{port}/web_dashboard.html")
        print("⏹️  按 Ctrl+C 停止服务器")
        
        subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")

def main():
    parser = argparse.ArgumentParser(description="FastChat 投票分析自动化脚本")
    parser.add_argument("--log-file", type=str, required=True, help="投票日志文件路径")
    parser.add_argument("--port", type=int, default=8080, help="Web服务器端口 (默认: 8080)")
    parser.add_argument("--no-web", action="store_true", help="只分析数据，不启动Web服务器")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.log_file):
        print(f"❌ 错误: 日志文件不存在: {args.log_file}")
        sys.exit(1)
    
    print("🚀 FastChat 投票分析自动化脚本")
    print("=" * 50)
    
    # 分析投票数据
    success = analyze_vote_data(args.log_file)
    
    if not success:
        print("❌ 数据分析失败，退出程序")
        sys.exit(1)
    
    # 创建Web展示页面
    create_web_dashboard()
    
    # 启动Web服务器
    if not args.no_web:
        start_web_server(args.port)
    else:
        print("\n✅ 分析完成！")
        print("📊 生成的文件:")
        print("  - vote_analysis.csv (投票统计)")
        print("  - elo_rankings.csv (ELO排名)")
        print("  - web_dashboard.html (Web展示页面)")
        print("\n🌐 要查看Web展示，请运行:")
        print(f"   python -m http.server {args.port}")
        print(f"   然后在浏览器中访问: http://localhost:{args.port}/web_dashboard.html")

if __name__ == "__main__":
    main() 