"""
Simplified report display component for FastChat Web UI.
Displays complete HTML reports with proper chart support.
"""

import subprocess
import os
import gradio as gr
from pathlib import Path
import re

def run_generate_report(force_refresh=False):
    """运行generate_report.py脚本生成报告"""
    try:
        # 获取项目根目录路径
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # 从 fastchat/serve/ 回到项目根目录
        
        print(f"项目根目录: {project_root}")
        print(f"当前工作目录: {os.getcwd()}")
        
        # 强制刷新时清除缓存文件
        if force_refresh:
            cache_file = project_root / ".log_cache.json"
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    print("🗑️  已清除缓存文件，确保获取最新数据")
                except Exception as e:
                    print(f"⚠️  清除缓存文件失败: {e}")
        
        # 构建命令参数
        cmd_args = ['python', 'generate_report.py']
        
        if force_refresh:
            # 强制刷新模式：使用累积分析确保获取最新数据
            cmd_args.append('--cumulative')
            cmd_args.append('--force')
            print("🔄 强制刷新模式：使用累积分析获取最新数据")
        else:
            # 正常模式：使用累积分析模式
            cmd_args.append('--cumulative')
            print("📊 使用累积分析模式获取完整数据")
        
        # 运行generate_report.py脚本
        result = subprocess.run(cmd_args, 
                              capture_output=True, text=True, cwd=str(project_root))
        
        print(f"命令返回码: {result.returncode}")
        print(f"标准输出: {result.stdout}")
        print(f"标准错误: {result.stderr}")
        
        if result.returncode == 0:
            # 查找最新生成的报告文件 - 从reports目录
            reports_dir = project_root / "reports"
            print(f"检查报告目录: {reports_dir}")
            
            if reports_dir.exists():
                # 找到最新的报告目录
                report_dirs = [d for d in reports_dir.iterdir() if d.is_dir()]
                print(f"找到 {len(report_dirs)} 个报告目录")
                
                if report_dirs:
                    latest_dir = max(report_dirs, key=lambda x: x.stat().st_mtime)
                    print(f"最新报告目录: {latest_dir}")
                    
                    report_file = latest_dir / "report.html"
                    print(f"报告文件路径: {report_file}")
                    
                    if report_file.exists():
                        print(f"✅ 找到报告文件: {report_file}")
                        status_msg = "✅ FastChat 投票分析报告生成成功！已处理累积数据，包含最新投票信息。"
                        if force_refresh:
                            status_msg += " (强制刷新)"
                        return status_msg, str(report_file)
                    else:
                        print(f"❌ 报告文件不存在: {report_file}")
            
            # 备用：从static/reports目录查找
            static_reports_dir = project_root / "static" / "reports"
            print(f"检查静态报告目录: {static_reports_dir}")
            
            if static_reports_dir.exists():
                html_files = list(static_reports_dir.glob("*.html"))
                print(f"找到 {len(html_files)} 个HTML文件")
                
                if html_files:
                    latest_report = max(html_files, key=os.path.getmtime)
                    print(f"最新静态报告: {latest_report}")
                    status_msg = "✅ FastChat 投票分析报告生成成功！已处理累积数据，包含最新投票信息。"
                    if force_refresh:
                        status_msg += " (强制刷新)"
                    return status_msg, str(latest_report)
            
            return "❌ 未找到生成的HTML报告文件，请检查日志输出", ""
        else:
            # 提供更详细的错误信息
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            if not error_msg:
                error_msg = "未知错误"
            return f"❌ 报告生成失败: {error_msg}", ""
    except Exception as e:
        print(f"执行异常: {str(e)}")
        return f"❌ 执行错误: {str(e)}", ""

def generate_html_report(force_refresh=False):
    """生成FastChat投票分析HTML报告"""
    # 先运行报告生成
    status_msg, report_path = run_generate_report(force_refresh=force_refresh)
    
    if "成功" in status_msg and report_path:
        try:
            # 读取生成的HTML文件
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # 从HTML中提取动态数据
            vote_data = extract_vote_data_from_html(html_content)
            model_data = extract_model_data_from_html(html_content)
            
            # 修复Chart.js CDN链接，使用更可靠的CDN
            html_content = html_content.replace(
                'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js',
                'https://cdn.jsdelivr.net/npm/chart.js'
            )
            
            # 修复黑色覆盖问题 - 移除过度的通用CSS规则
            html_content = html_content.replace(
                '.content * {\n                color: #ffffff !important;\n            }',
                '/* 修复过度的通用样式 - 移除 .content * 规则 */'
            )
            
            # 注入强制黑色主题样式 - 解决ELO排名表白色背景问题
            theme_fix_css = '''
            <style>
            /* 强制优化配色主题样式 - 提高对比度和可读性 */
            .report-html-container body {
                background-color: #0a0f1c !important;
                color: #ffffff !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            }
            
            .report-html-container .content {
                background-color: #0a0f1c !important;
                color: #ffffff !important;
            }
            
            /* 强制覆盖所有表格样式 - 更高对比度 */
            .report-html-container table, .report-html-container #eloTable, .report-html-container #detailTable {
                background: #0a0f1c !important;
                color: #ffffff !important;
                border-collapse: collapse !important;
                border: 2px solid #2d3748 !important;
                border-radius: 8px !important;
                overflow: hidden !important;
            }
            
            .report-html-container table th, .report-html-container #eloTable th, .report-html-container #detailTable th {
                background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
                color: #ffffff !important;
                border-bottom: 2px solid #1e40af !important;
                padding: 16px 12px !important;
                font-weight: 700 !important;
                text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
                font-size: 14px !important;
            }
            
            .report-html-container table td, .report-html-container #eloTable td, .report-html-container #detailTable td {
                background: #0a0f1c !important;
                color: #ffffff !important;
                border-bottom: 1px solid #2d3748 !important;
                padding: 16px 12px !important;
                font-size: 14px !important;
                font-weight: 500 !important;
            }
            
            .report-html-container table tbody tr, .report-html-container #eloTable tbody tr, .report-html-container #detailTable tbody tr {
                background: #0a0f1c !important;
                color: #ffffff !important;
                transition: all 0.3s ease !important;
            }
            
            .report-html-container table tbody tr:nth-child(even), .report-html-container #eloTable tbody tr:nth-child(even), .report-html-container #detailTable tbody tr:nth-child(even) {
                background: #16213e !important;
            }
            
            .report-html-container table tbody tr:hover, .report-html-container #eloTable tbody tr:hover, .report-html-container #detailTable tbody tr:hover {
                background: #2563eb !important;
                color: #ffffff !important;
                transform: translateX(4px) !important;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
            }
            
            /* 强制覆盖表格中的特殊样式类 - 更鲜明的颜色 */
            .report-html-container .winner {
                color: #22c55e !important;
                font-weight: 700 !important;
                text-shadow: 0 1px 3px rgba(34, 197, 94, 0.5) !important;
            }
            
            .report-html-container .loser {
                color: #ef4444 !important;
                font-weight: 700 !important;
                text-shadow: 0 1px 3px rgba(239, 68, 68, 0.5) !important;
            }
            
            .report-html-container .tie {
                color: #f59e0b !important;
                font-weight: 700 !important;
                text-shadow: 0 1px 3px rgba(245, 158, 11, 0.5) !important;
            }
            
            .report-html-container .model-name {
                color: #60a5fa !important;
                font-weight: 700 !important;
                text-shadow: 0 1px 3px rgba(96, 165, 250, 0.5) !important;
            }
            
            /* 强制覆盖容器样式 - 更深的背景 */
            .report-html-container .table-container, .report-html-container .chart-container {
                background: #0a0f1c !important;
                color: #ffffff !important;
                border: 2px solid #2d3748 !important;
                border-radius: 12px !important;
                padding: 20px !important;
                margin: 20px 0 !important;
            }
            
            .report-html-container .chart-title, .report-html-container .table-title {
                color: #ffffff !important;
                font-weight: 700 !important;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5) !important;
                font-size: 18px !important;
                margin-bottom: 16px !important;
            }
            
            .report-html-container .stat-card {
                background: linear-gradient(135deg, #2196f3 0%, #6ec6ff 100%) !important;
                color: #222 !important;
                border: 2px solid #90caf9 !important;
                border-radius: 16px !important;
                box-shadow: 0 4px 16px rgba(33, 150, 243, 0.15) !important;
                padding: 24px !important;
                margin: 18px 0 !important;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background-color: transparent !important;
            }
            .report-html-container .stat-value {
                color: #222 !important;
                font-weight: 900 !important;
                font-size: 38px !important;
                text-shadow: none !important;
                margin-bottom: 8px;
            }
            .report-html-container .stat-label {
                color: #222 !important;
                font-weight: 600 !important;
                font-size: 18px !important;
                text-shadow: none !important;
            }
            
            .report-html-container .footer {
                background: #0a0f1c !important;
                color: #ffffff !important;
                border-top: 2px solid #2d3748 !important;
                padding: 20px !important;
                margin-top: 40px !important;
            }
            
            /* 强制覆盖任何可能的白色背景 */
            .report-html-container * {
                background-color: transparent !important;
            }
            
            .report-html-container body, .report-html-container .content, .report-html-container .table-container, .report-html-container .chart-container {
                background-color: #0a0f1c !important;
            }
            
            .report-html-container .content {
                background-color: #0a0f1c !important;
                padding: 20px !important;
            }
            
            .report-html-container .table-container {
                background-color: #0a0f1c !important;
            }
            
            .report-html-container .chart-container {
                background-color: #0a0f1c !important;
            }
            
            /* 图表容器优化 - 更深的背景 */
            .report-html-container .chart-container canvas {
                background: #1a1a2e !important;
                border-radius: 8px !important;
            }
            
            /* 统计卡片网格优化 */
            .report-html-container .stats-grid {
                display: grid !important;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important;
                gap: 20px !important;
                margin: 20px 0 !important;
            }
            
            /* 修正：去除统计卡片上方的黑色蒙层或深色背景，确保蓝色渐变可见 */
            .report-html-container .stats-grid {
                background: transparent !important;
            }
            .report-html-container .stat-card {
                background: linear-gradient(135deg, #2196f3 0%, #6ec6ff 100%) !important;
                color: #222 !important;
                border: 2px solid #90caf9 !important;
                border-radius: 16px !important;
                box-shadow: 0 4px 16px rgba(33, 150, 243, 0.15) !important;
                padding: 24px !important;
                margin: 18px 0 !important;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                background-color: transparent !important;
            }
            
            /* 标题样式优化 */
            .report-html-container h1, .report-html-container h2, .report-html-container h3, .report-html-container h4, .report-html-container h5, .report-html-container h6 {
                color: #ffffff !important;
                font-weight: 700 !important;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5) !important;
            }
            
            /* 段落文本优化 */
            .report-html-container p {
                color: #e2e8f0 !important;
                line-height: 1.6 !important;
                font-size: 14px !important;
            }
            
            /* 滚动条样式优化 */
            .report-html-container *::-webkit-scrollbar {
                width: 12px;
                height: 12px;
            }
            
            .report-html-container *::-webkit-scrollbar-track {
                background: #1a1a2e;
                border-radius: 6px;
            }
            
            .report-html-container *::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
                border-radius: 6px;
                border: 2px solid #1a1a2e;
            }
            
            .report-html-container *::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            }
            
            /* 响应式优化 */
            @media (max-width: 768px) {
                .report-html-container table th, .report-html-container table td {
                    padding: 12px 8px !important;
                    font-size: 12px !important;
                }
                
                .report-html-container .stat-value {
                    font-size: 20px !important;
                }
                
                .report-html-container .chart-title, .report-html-container .table-title {
                    font-size: 16px !important;
                }
            }
            </style>
            '''
            
            # 在head标签中注入样式
            if '<head>' in html_content:
                html_content = html_content.replace('<head>', f'<head>{theme_fix_css}')
            else:
                # 如果没有head标签，在开头添加
                html_content = theme_fix_css + html_content
            
            # 移除原始的图表初始化脚本，避免冲突
            # 移除原始的script标签（但保留Chart.js CDN）
            html_content = re.sub(r'<script>.*?function initCharts\(\).*?</script>', '', html_content, flags=re.DOTALL)
            
            # 在</body>标签前添加唯一的强制图表初始化代码
            force_init_script = f'''
    <script>
        // 唯一的图表初始化脚本 - 避免冲突
        let chartsInitialized = false;
        let initAttempts = 0;
        
        function initializeCharts() {{
            initAttempts++;
            console.log(`图表初始化尝试 #${{initAttempts}}`);
            
            if (chartsInitialized) {{
                console.log('图表已经初始化，跳过重复初始化');
                return;
            }}
            
            if (typeof Chart === 'undefined') {{
                console.log('Chart.js 还未加载，等待...');
                if (initAttempts < 20) {{
                    setTimeout(initializeCharts, 500);
                }}
                return;
            }}
            
            console.log('Chart.js 已加载，版本:', Chart.version);
            console.log('开始初始化图表...');
            
            try {{
                // 投票类型分布图表
                const voteCanvas = document.getElementById('voteTypeChart');
                console.log('投票图表Canvas:', voteCanvas);
                if (voteCanvas) {{
                    // 清除可能存在的旧图表
                    Chart.getChart(voteCanvas)?.destroy();
                    
                    const voteCtx = voteCanvas.getContext('2d');
                    console.log('投票图表Context:', voteCtx);
                    
                    const voteChart = new Chart(voteCtx, {{
                        type: 'doughnut',
                        data: {{
                            labels: ['左方获胜', '右方获胜', '平局'],
                            datasets: [{{
                                data: [{vote_data['leftvote']}, {vote_data['rightvote']}, {vote_data['tievote']}],
                                backgroundColor: ['#28a745', '#dc3545', '#ffc107'],
                                borderWidth: 2,
                                borderColor: '#fff'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{
                                        padding: 10,
                                        usePointStyle: true
                                    }}
                                }}
                            }}
                        }}
                    }});
                    console.log('✅ 投票分布图表创建成功:', voteChart);
                }} else {{
                    console.error('❌ 找不到投票图表Canvas元素');
                }}
                
                // 模型胜率对比图表
                const winRateCanvas = document.getElementById('winRateChart');
                console.log('胜率图表Canvas:', winRateCanvas);
                if (winRateCanvas) {{
                    // 清除可能存在的旧图表
                    Chart.getChart(winRateCanvas)?.destroy();
                    
                    const winRateCtx = winRateCanvas.getContext('2d');
                    console.log('胜率图表Context:', winRateCtx);
                    
                    const winRateChart = new Chart(winRateCtx, {{
                        type: 'bar',
                        data: {{
                            labels: {model_data['labels']},
                            datasets: [{{
                                label: '胜率 (%)',
                                data: {model_data['winRates']},
                                backgroundColor: {model_data['barColors']},
                                borderColor: {model_data['borderColors']},
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    max: 100,
                                    ticks: {{
                                        callback: function(value) {{
                                            return value + '%';
                                        }}
                                    }}
                                }}
                            }},
                            plugins: {{
                                legend: {{
                                    display: false
                                }}
                            }}
                        }}
                    }});
                    console.log('✅ 胜率对比图表创建成功:', winRateChart);
                }} else {{
                    console.error('❌ 找不到胜率图表Canvas元素');
                }}
                
                chartsInitialized = true;
                console.log('✅ 所有图表初始化完成');
                
                // 验证图表是否真的显示了
                setTimeout(function() {{
                    const voteChart = Chart.getChart('voteTypeChart');
                    const winChart = Chart.getChart('winRateChart');
                    console.log('投票图表状态:', voteChart ? '已创建' : '未找到');
                    console.log('胜率图表状态:', winChart ? '已创建' : '未找到');
                }}, 1000);
                
            }} catch (error) {{
                console.error('❌ 图表初始化失败:', error);
                console.error('错误堆栈:', error.stack);
            }}
        }}
        
        // 更强的触发机制
        function startInitialization() {{
            console.log('开始图表初始化流程...');
            
            // 立即尝试
            initializeCharts();
            
            // DOM加载完成后尝试
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', function() {{
                    console.log('DOM加载完成，尝试初始化图表...');
                    setTimeout(initializeCharts, 100);
                }});
            }}
            
            // 窗口加载完成后尝试
            if (document.readyState !== 'complete') {{
                window.addEventListener('load', function() {{
                    console.log('窗口加载完成，尝试初始化图表...');
                    setTimeout(initializeCharts, 200);
                }});
            }}
            
            // 定时重试机制
            let retryCount = 0;
            const maxRetries = 10;
            const retryInterval = setInterval(function() {{
                retryCount++;
                console.log(`定时重试 #${{retryCount}}`);
                
                if (!chartsInitialized && retryCount < maxRetries) {{
                    initializeCharts();
                }} else {{
                    clearInterval(retryInterval);
                    if (chartsInitialized) {{
                        console.log('✅ 图表初始化成功完成');
                    }} else {{
                        console.log('❌ 图表初始化最终失败');
                    }}
                }}
            }}, 1000);
        }}
        
        // 启动初始化
        startInitialization();
    </script>
    '''
            
            # 在</body>标签前插入脚本
            html_content = html_content.replace('</body>', force_init_script + '\n</body>')
            
            return f"✅ 报告生成成功！{status_msg}", html_content
        except Exception as e:
            return f"❌ 读取报告失败: {str(e)}", ""
    else:
        return status_msg, ""

def generate_html_report_force_refresh():
    """强制刷新并生成最新的投票分析报告"""
    return generate_html_report(force_refresh=True)

def extract_vote_data_from_html(html_content):
    """从HTML内容中提取投票分布数据"""
    try:
        # 使用正则表达式提取voteDistributionData
        vote_pattern = r'const voteDistributionData = \{\s*leftvote: (\d+),\s*rightvote: (\d+),\s*tievote: (\d+)\s*\};'
        match = re.search(vote_pattern, html_content)
        if match:
            return {
                'leftvote': int(match.group(1)),
                'rightvote': int(match.group(2)),
                'tievote': int(match.group(3))
            }
    except Exception as e:
        print(f"提取投票数据失败: {e}")
    
    # 默认数据
    return {'leftvote': 0, 'rightvote': 0, 'tievote': 0}

def extract_model_data_from_html(html_content):
    """从HTML内容中提取模型数据"""
    try:
        # 使用正则表达式提取modelData
        model_pattern = r'const modelData = \{\s*labels: (\[.*?\]),\s*winRates: (\[.*?\]),\s*barColors: (\[.*?\]),\s*borderColors: (\[.*?\])\s*\};'
        match = re.search(model_pattern, html_content, re.DOTALL)
        if match:
            return {
                'labels': match.group(1),
                'winRates': match.group(2),
                'barColors': match.group(3),
                'borderColors': match.group(4)
            }
    except Exception as e:
        print(f"提取模型数据失败: {e}")
    
    # 默认数据
    return {
        'labels': '["Model A", "Model B"]',
        'winRates': '[50, 50]',
        'barColors': '["rgba(40, 167, 69, 0.8)", "rgba(102, 126, 234, 0.8)"]',
        'borderColors': '["rgba(40, 167, 69, 1)", "rgba(102, 126, 234, 1)"]'
    }

def refresh_latest_report():
    """刷新最新报告（不重新生成）"""
    try:
        # 获取项目根目录路径
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # 从 fastchat/serve/ 回到项目根目录
        
        print(f"刷新报告 - 项目根目录: {project_root}")
        
        # 查找最新生成的报告文件
        reports_dir = project_root / "reports"
        print(f"检查报告目录: {reports_dir}")
        
        if reports_dir.exists():
            # 找到最新的报告目录
            report_dirs = [d for d in reports_dir.iterdir() if d.is_dir()]
            print(f"找到 {len(report_dirs)} 个报告目录")
            
            if report_dirs:
                latest_dir = max(report_dirs, key=lambda x: x.stat().st_mtime)
                print(f"最新报告目录: {latest_dir}")
                
                report_file = latest_dir / "report.html"
                print(f"报告文件路径: {report_file}")
                
                if report_file.exists():
                    print(f"✅ 找到报告文件: {report_file}")
                    
                    # 读取HTML内容
                    with open(report_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # 从HTML中提取动态数据
                    vote_data = extract_vote_data_from_html(html_content)
                    model_data = extract_model_data_from_html(html_content)
                    
                    print(f"提取的投票数据: {vote_data}")
                    print(f"提取的模型数据: {model_data}")
                    
                    # 修复Chart.js CDN链接
                    html_content = html_content.replace(
                        'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js',
                        'https://cdn.jsdelivr.net/npm/chart.js'
                    )
                    
                    # 修复黑色覆盖问题 - 移除过度的通用CSS规则
                    html_content = html_content.replace(
                        '.content * {\n                color: #ffffff !important;\n            }',
                        '/* 修复过度的通用样式 - 移除 .content * 规则 */'
                    )
                    
                    # 注入强制黑色主题样式 - 解决ELO排名表白色背景问题
                    theme_fix_css = '''
                    <style>
                    /* 优化配色方案：柔和深色背景+高亮色，提升可读性和现代感 */
                    .report-html-container body {
                        background-color: #181c24 !important;
                        color: #f3f6fa !important;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                    }
                    .report-html-container .content, .report-html-container .table-container, .report-html-container .chart-container {
                        background-color: #181c24 !important;
                        color: #f3f6fa !important;
                    }
                    .report-html-container table, .report-html-container #eloTable, .report-html-container #detailTable {
                        background: #23293a !important;
                        color: #f3f6fa !important;
                        border-collapse: collapse !important;
                        border: 2px solid #3b4252 !important;
                        border-radius: 10px !important;
                        overflow: hidden !important;
                    }
                    .report-html-container table th, .report-html-container #eloTable th, .report-html-container #detailTable th {
                        background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%) !important;
                        color: #fff !important;
                        border-bottom: 2px solid #2563eb !important;
                        padding: 16px 12px !important;
                        font-weight: 700 !important;
                        text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
                        font-size: 15px !important;
                    }
                    .report-html-container table td, .report-html-container #eloTable td, .report-html-container #detailTable td {
                        background: #23293a !important;
                        color: #f3f6fa !important;
                        border-bottom: 1px solid #3b4252 !important;
                        padding: 14px 10px !important;
                        font-size: 14px !important;
                        font-weight: 500 !important;
                    }
                    .report-html-container table tbody tr:nth-child(even), .report-html-container #eloTable tbody tr:nth-child(even), .report-html-container #detailTable tbody tr:nth-child(even) {
                        background: #20232b !important;
                    }
                    .report-html-container table tbody tr:hover, .report-html-container #eloTable tbody tr:hover, .report-html-container #detailTable tbody tr:hover {
                        background: #2563eb !important;
                        color: #fff !important;
                        box-shadow: 0 4px 12px rgba(37,99,235,0.15) !important;
                    }
                    .report-html-container .winner { color: #22c55e !important; font-weight: 700 !important; }
                    .report-html-container .loser { color: #ef4444 !important; font-weight: 700 !important; }
                    .report-html-container .tie { color: #f59e0b !important; font-weight: 700 !important; }
                    .report-html-container .model-name { color: #60a5fa !important; font-weight: 700 !important; }
                    .report-html-container .table-container, .report-html-container .chart-container {
                        background: #181c24 !important;
                        color: #f3f6fa !important;
                        border: 2px solid #3b4252 !important;
                        border-radius: 12px !important;
                        padding: 18px !important;
                        margin: 18px 0 !important;
                    }
                    .report-html-container .chart-title, .report-html-container .table-title {
                        color: #fff !important;
                        font-weight: 700 !important;
                        font-size: 18px !important;
                        margin-bottom: 14px !important;
                    }
                    .report-html-container .stat-card {
                        background: linear-gradient(135deg, #23293a 0%, #181c24 100%) !important;
                        color: #f3f6fa !important;
                        border: 2px solid #2563eb !important;
                        border-radius: 12px !important;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
                        padding: 18px !important;
                        margin: 14px 0 !important;
                    }
                    .report-html-container .stat-value { color: #60a5fa !important; font-weight: 900 !important; font-size: 22px !important; }
                    .report-html-container .stat-label { color: #e2e8f0 !important; font-weight: 600 !important; font-size: 13px !important; }
                    .report-html-container .footer {
                        background: #181c24 !important;
                        color: #f3f6fa !important;
                        border-top: 2px solid #3b4252 !important;
                        padding: 18px !important;
                        margin-top: 32px !important;
                    }
                    .report-html-container * { background-color: transparent !important; }
                    .report-html-container .chart-container canvas { background: #23293a !important; border-radius: 8px !important; }
                    .report-html-container .stats-grid { display: grid !important; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important; gap: 18px !important; margin: 18px 0 !important; }
                    .report-html-container h1, .report-html-container h2, .report-html-container h3, .report-html-container h4, .report-html-container h5, .report-html-container h6 { color: #fff !important; font-weight: 700 !important; }
                    .report-html-container p { color: #e2e8f0 !important; line-height: 1.6 !important; font-size: 14px !important; }
                    .report-html-container *::-webkit-scrollbar { width: 10px; height: 10px; }
                    .report-html-container *::-webkit-scrollbar-track { background: #23293a; border-radius: 5px; }
                    .report-html-container *::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%); border-radius: 5px; border: 2px solid #23293a; }
                    .report-html-container *::-webkit-scrollbar-thumb:hover { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
                    @media (max-width: 768px) {
                        .report-html-container table th, .report-html-container table td { padding: 10px 6px !important; font-size: 12px !important; }
                        .report-html-container .stat-value { font-size: 18px !important; }
                        .report-html-container .chart-title, .report-html-container .table-title { font-size: 15px !important; }
                    }
                    </style>
                    '''
                    # 在head标签中注入样式
                    if '<head>' in html_content:
                        html_content = html_content.replace('<head>', f'<head>{theme_fix_css}')
                    else:
                        html_content = theme_fix_css + html_content
                    # 移除原始的图表初始化脚本，避免冲突
                    html_content = re.sub(r'<script>.*?function initCharts\(\).*?</script>', '', html_content, flags=re.DOTALL)
                    # 在</body>标签前添加唯一的强制图表初始化代码
                    force_init_script = f'''
    <script>
        // 唯一的图表初始化脚本 - 避免冲突
        let chartsInitialized = false;
        let initAttempts = 0;
        function initializeCharts() {{
            initAttempts++;
            if (chartsInitialized) return;
            if (typeof Chart === 'undefined') {{
                if (initAttempts < 20) setTimeout(initializeCharts, 500);
                return;
            }}
            try {{
                const voteCanvas = document.getElementById('voteTypeChart');
                if (voteCanvas) {{ Chart.getChart(voteCanvas)?.destroy();
                    const voteCtx = voteCanvas.getContext('2d');
                    new Chart(voteCtx, {{ type: 'doughnut', data: {{ labels: ['左方获胜', '右方获胜', '平局'], datasets: [{{ data: [{vote_data['leftvote']}, {vote_data['rightvote']}, {vote_data['tievote']}], backgroundColor: ['#22c55e', '#2563eb', '#f59e0b'], borderWidth: 2, borderColor: '#fff' }}] }}, options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ padding: 10, usePointStyle: true }} }} }} }} }});
                const winRateCanvas = document.getElementById('winRateChart');
                if (winRateCanvas) {{ Chart.getChart(winRateCanvas)?.destroy();
                    const winRateCtx = winRateCanvas.getContext('2d');
                    new Chart(winRateCtx, {{ type: 'bar', data: {{ labels: {model_data['labels']}, datasets: [{{ label: '胜率 (%)', data: {model_data['winRates']}, backgroundColor: {model_data['barColors']}, borderColor: {model_data['borderColors']}, borderWidth: 2 }}] }}, options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: function(value) {{ return value + '%' }} }} }} }}, plugins: {{ legend: {{ display: false }} }} }} }});
                chartsInitialized = true;
            }} catch (error) {{}}
        }}
        function startInitialization() {{
            initializeCharts();
            if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', function() {{ setTimeout(initializeCharts, 100); }}); }}
            if (document.readyState !== 'complete') {{ window.addEventListener('load', function() {{ setTimeout(initializeCharts, 200); }}); }}
            let retryCount = 0; const maxRetries = 10; const retryInterval = setInterval(function() {{ retryCount++; if (!chartsInitialized && retryCount < maxRetries) {{ initializeCharts(); }} else {{ clearInterval(retryInterval); }} }}, 1000);
        }}
        startInitialization();
    </script>
    </body>'''
                    html_content = html_content.replace('</body>', force_init_script)
                    return f"✅ 最新报告已刷新！累积数据已更新，包含最新投票信息。", html_content
                else:
                    print(f"❌ 报告文件不存在: {report_file}")
        
        # 备用：从static/reports目录查找
        static_reports_dir = project_root / "static" / "reports"
        print(f"检查静态报告目录: {static_reports_dir}")
        
        if static_reports_dir.exists():
            html_files = list(static_reports_dir.glob("*.html"))
            print(f"找到 {len(html_files)} 个HTML文件")
            
            if html_files:
                latest_report = max(html_files, key=os.path.getmtime)
                print(f"最新静态报告: {latest_report}")
                
                # 读取HTML内容
                with open(latest_report, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 注入强制黑色主题样式 - 解决ELO排名表白色背景问题
                theme_fix_css = '''
                <style>
                /* 优化配色方案：柔和深色背景+高亮色，提升可读性和现代感 */
                .report-html-container body {
                    background-color: #181c24 !important;
                    color: #f3f6fa !important;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                }
                .report-html-container .content, .report-html-container .table-container, .report-html-container .chart-container {
                    background-color: #181c24 !important;
                    color: #f3f6fa !important;
                }
                .report-html-container table, .report-html-container #eloTable, .report-html-container #detailTable {
                    background: #23293a !important;
                    color: #f3f6fa !important;
                    border-collapse: collapse !important;
                    border: 2px solid #3b4252 !important;
                    border-radius: 10px !important;
                    overflow: hidden !important;
                }
                .report-html-container table th, .report-html-container #eloTable th, .report-html-container #detailTable th {
                    background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%) !important;
                    color: #fff !important;
                    border-bottom: 2px solid #2563eb !important;
                    padding: 16px 12px !important;
                    font-weight: 700 !important;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.3) !important;
                    font-size: 15px !important;
                }
                .report-html-container table td, .report-html-container #eloTable td, .report-html-container #detailTable td {
                    background: #23293a !important;
                    color: #f3f6fa !important;
                    border-bottom: 1px solid #3b4252 !important;
                    padding: 14px 10px !important;
                    font-size: 14px !important;
                    font-weight: 500 !important;
                }
                .report-html-container table tbody tr:nth-child(even), .report-html-container #eloTable tbody tr:nth-child(even), .report-html-container #detailTable tbody tr:nth-child(even) {
                    background: #20232b !important;
                }
                .report-html-container table tbody tr:hover, .report-html-container #eloTable tbody tr:hover, .report-html-container #detailTable tbody tr:hover {
                    background: #2563eb !important;
                    color: #fff !important;
                    box-shadow: 0 4px 12px rgba(37,99,235,0.15) !important;
                }
                .report-html-container .winner { color: #22c55e !important; font-weight: 700 !important; }
                .report-html-container .loser { color: #ef4444 !important; font-weight: 700 !important; }
                .report-html-container .tie { color: #f59e0b !important; font-weight: 700 !important; }
                .report-html-container .model-name { color: #60a5fa !important; font-weight: 700 !important; }
                .report-html-container .table-container, .report-html-container .chart-container {
                    background: #181c24 !important;
                    color: #f3f6fa !important;
                    border: 2px solid #3b4252 !important;
                    border-radius: 12px !important;
                    padding: 18px !important;
                    margin: 18px 0 !important;
                }
                .report-html-container .chart-title, .report-html-container .table-title {
                    color: #fff !important;
                    font-weight: 700 !important;
                    font-size: 18px !important;
                    margin-bottom: 14px !important;
                }
                .report-html-container .stat-card {
                    background: linear-gradient(135deg, #23293a 0%, #181c24 100%) !important;
                    color: #f3f6fa !important;
                    border: 2px solid #2563eb !important;
                    border-radius: 12px !important;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
                    padding: 18px !important;
                    margin: 14px 0 !important;
                }
                .report-html-container .stat-value { color: #60a5fa !important; font-weight: 900 !important; font-size: 22px !important; }
                .report-html-container .stat-label { color: #e2e8f0 !important; font-weight: 600 !important; font-size: 13px !important; }
                .report-html-container .footer {
                    background: #181c24 !important;
                    color: #f3f6fa !important;
                    border-top: 2px solid #3b4252 !important;
                    padding: 18px !important;
                    margin-top: 32px !important;
                }
                .report-html-container * { background-color: transparent !important; }
                .report-html-container .chart-container canvas { background: #23293a !important; border-radius: 8px !important; }
                .report-html-container .stats-grid { display: grid !important; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important; gap: 18px !important; margin: 18px 0 !important; }
                .report-html-container h1, .report-html-container h2, .report-html-container h3, .report-html-container h4, .report-html-container h5, .report-html-container h6 { color: #fff !important; font-weight: 700 !important; }
                .report-html-container p { color: #e2e8f0 !important; line-height: 1.6 !important; font-size: 14px !important; }
                .report-html-container *::-webkit-scrollbar { width: 10px; height: 10px; }
                .report-html-container *::-webkit-scrollbar-track { background: #23293a; border-radius: 5px; }
                .report-html-container *::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%); border-radius: 5px; border: 2px solid #23293a; }
                .report-html-container *::-webkit-scrollbar-thumb:hover { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); }
                @media (max-width: 768px) {
                    .report-html-container table th, .report-html-container table td { padding: 10px 6px !important; font-size: 12px !important; }
                    .report-html-container .stat-value { font-size: 18px !important; }
                    .report-html-container .chart-title, .report-html-container .table-title { font-size: 15px !important; }
                }
                </style>
                '''
                # 在head标签中注入样式
                if '<head>' in html_content:
                    html_content = html_content.replace('<head>', f'<head>{theme_fix_css}')
                else:
                    html_content = theme_fix_css + html_content
                # 移除原始的图表初始化脚本，避免冲突
                html_content = re.sub(r'<script>.*?function initCharts\(\).*?</script>', '', html_content, flags=re.DOTALL)
                # 在</body>标签前添加唯一的强制图表初始化代码
                force_init_script = f'''
    <script>
        // 唯一的图表初始化脚本 - 避免冲突
        let chartsInitialized = false;
        let initAttempts = 0;
        function initializeCharts() {{
            initAttempts++;
            if (chartsInitialized) return;
            if (typeof Chart === 'undefined') {{
                if (initAttempts < 20) setTimeout(initializeCharts, 500);
                return;
            }}
            try {{
                const voteCanvas = document.getElementById('voteTypeChart');
                if (voteCanvas) {{ Chart.getChart(voteCanvas)?.destroy();
                    const voteCtx = voteCanvas.getContext('2d');
                    new Chart(voteCtx, {{ type: 'doughnut', data: {{ labels: ['左方获胜', '右方获胜', '平局'], datasets: [{{ data: [{vote_data['leftvote']}, {vote_data['rightvote']}, {vote_data['tievote']}], backgroundColor: ['#22c55e', '#2563eb', '#f59e0b'], borderWidth: 2, borderColor: '#fff' }}] }}, options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ position: 'bottom', labels: {{ padding: 10, usePointStyle: true }} }} }} }} }});
                const winRateCanvas = document.getElementById('winRateChart');
                if (winRateCanvas) {{ Chart.getChart(winRateCanvas)?.destroy();
                    const winRateCtx = winRateCanvas.getContext('2d');
                    new Chart(winRateCtx, {{ type: 'bar', data: {{ labels: {model_data['labels']}, datasets: [{{ label: '胜率 (%)', data: {model_data['winRates']}, backgroundColor: {model_data['barColors']}, borderColor: {model_data['borderColors']}, borderWidth: 2 }}] }}, options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, max: 100, ticks: {{ callback: function(value) {{ return value + '%' }} }} }} }}, plugins: {{ legend: {{ display: false }} }} }} }});
                chartsInitialized = true;
            }} catch (error) {{}}
        }}
        function startInitialization() {{
            initializeCharts();
            if (document.readyState === 'loading') {{ document.addEventListener('DOMContentLoaded', function() {{ setTimeout(initializeCharts, 100); }}); }}
            if (document.readyState !== 'complete') {{ window.addEventListener('load', function() {{ setTimeout(initializeCharts, 200); }}); }}
            let retryCount = 0; const maxRetries = 10; const retryInterval = setInterval(function() {{ retryCount++; if (!chartsInitialized && retryCount < maxRetries) {{ initializeCharts(); }} else {{ clearInterval(retryInterval); }} }}, 1000);
        }}
        startInitialization();
    </script>
    </body>'''
                html_content = html_content.replace('</body>', force_init_script)
                return f"✅ 最新报告已刷新！累积数据已更新，包含最新投票信息。", html_content
        
        return "❌ 未找到任何报告文件", "<p>请先生成报告</p>"
    except Exception as e:
        print(f"刷新报告异常: {str(e)}")
        return f"❌ 刷新报告失败: {str(e)}", "<p>刷新失败</p>"

def build_reports_tab():
    """构建FastChat投票分析报告标签页"""
    
    # 添加自定义CSS样式 - 只针对报告模块的优化配色
    css = """
    <style>
    /* 报告模块高对比度深色主题 - 提升可读性 */
    
    /* 主要内容区域 - 更深的背景 */
    .main-content {
        background: linear-gradient(135deg, #0a0f1c 0%, #1a1a2e 100%) !important;
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.8);
        margin: 10px;
        overflow: hidden;
        border: 2px solid #2563eb;
    }
    
    /* 移除全局白色字体，避免影响卡片内容 */
    /* .main-content * { color: #ffffff !important; } */
    /* 统计卡片专用：只保留蓝色渐变背景和深色字体 */
    .main-content .stat-card {
        background: linear-gradient(135deg, #2196f3 0%, #6ec6ff 100%) !important;
        color: #222 !important;
        border: 2px solid #90caf9 !important;
        border-radius: 16px !important;
        box-shadow: 0 4px 16px rgba(33, 150, 243, 0.15) !important;
        padding: 24px !important;
        margin: 18px 0 !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background-color: transparent !important;
    }
    .main-content .stat-value {
        color: #222 !important;
        font-weight: 900 !important;
        font-size: 28px !important;
        text-shadow: none !important;
        margin-bottom: 8px;
    }
    .main-content .stat-label {
        color: #222 !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        text-shadow: none !important;
    }
    
    .compact-info {
        font-size: 0.9em;
        line-height: 1.4;
        margin: 15px 0;
        padding: 16px;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        border-radius: 12px;
        border-left: 4px solid #2563eb;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        border: 2px solid rgba(37, 99, 235, 0.3);
        color: #ffffff !important;
    }
    
    .status-info {
        display: inline-block;
        padding: 10px 20px;
        background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%) !important;
        border-radius: 25px;
        border: 2px solid #60a5fa;
        font-size: 0.9em;
        margin-bottom: 15px;
        color: #ffffff !important;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.5);
        transition: all 0.3s ease;
    }
    
    .status-info:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.7);
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
    }
    
    .report-container {
        margin-top: 15px;
        border: 2px solid #2d3748;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6);
        background: #0a0f1c !important;
    }
    
    .header-section {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        color: #ffffff !important;
        padding: 25px;
        text-align: center;
        border-radius: 16px 16px 0 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .header-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 100%);
        pointer-events: none;
    }
    
    .header-section h2 {
        margin: 0;
        font-size: 2em;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.5);
        position: relative;
        z-index: 1;
        color: #ffffff !important;
    }
    
    .header-section p {
        margin: 10px 0 0 0;
        opacity: 0.95;
        font-size: 1.1em;
        font-weight: 400;
        position: relative;
        z-index: 1;
        color: #ffffff !important;
    }
    
    .button-row {
        padding: 20px 25px;
        margin-top: -5px;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
        border-bottom: 2px solid #2d3748;
    }
    
    /* 按钮样式优化 - 高对比度配色 */
    .button-row button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
        color: #ffffff !important;
        padding: 12px 24px !important;
        font-size: 0.95em !important;
        border: 2px solid transparent !important;
    }
    
    .button-row button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
    }
    
    /* 主要按钮 - 蓝色渐变 */
    .button-row button[variant="primary"] {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%) !important;
        border-color: #60a5fa !important;
        color: #ffffff !important;
    }
    
    .button-row button[variant="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%) !important;
        box-shadow: 0 8px 24px rgba(37, 99, 235, 0.6) !important;
        border-color: #93c5fd !important;
    }
    
    /* 次要按钮 - 紫色渐变 */
    .button-row button[variant="secondary"] {
        background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%) !important;
        border-color: #a78bfa !important;
        color: #ffffff !important;
    }
    
    .button-row button[variant="secondary"]:hover {
        background: linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%) !important;
        box-shadow: 0 8px 24px rgba(124, 58, 237, 0.6) !important;
        border-color: #c4b5fd !important;
    }
    
    .info-grid {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 20px;
        align-items: start;
        margin: 0;
    }
    
    .info-grid strong {
        color: #60a5fa !important;
        font-weight: 700;
    }
    
    .info-grid div {
        color: #ffffff !important;
        font-weight: 500;
    }
    
    /* 内容区域样式 - 更深的背景 */
    .content-wrapper {
        padding: 20px 25px;
        background: linear-gradient(135deg, #0a0f1c 0%, #1a1a2e 100%) !important;
    }
    
    /* 报告显示区域优化 - 深色主题 */
    .report-display {
        background: #0a0f1c !important;
        border-radius: 12px;
        padding: 0;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.6);
        border: 2px solid #2d3748;
    }
    
    /* 报告模块内的输入框样式 - 高对比度 */
    .main-content input,
    .main-content textarea,
    .main-content select {
        background: #1a1a2e !important;
        border: 2px solid #2d3748 !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        font-weight: 500 !important;
    }
    
    .main-content input:focus,
    .main-content textarea:focus,
    .main-content select:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.3) !important;
        background: #16213e !important;
    }
    
    /* 报告模块内的标签样式 */
    .main-content label {
        color: #ffffff !important;
        font-weight: 600 !important;
    }
    
    /* 滚动条样式优化 - 高对比度 */
    .main-content *::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    .main-content *::-webkit-scrollbar-track {
        background: #1a1a2e;
        border-radius: 6px;
    }
    
    .main-content *::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        border-radius: 6px;
        border: 2px solid #1a1a2e;
    }
    
    .main-content *::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    }
    
    /* 响应式设计 */
    @media (max-width: 768px) {
        .header-section {
            padding: 20px 15px;
        }
        
        .header-section h2 {
            font-size: 1.6em;
        }
        
        .button-row {
            padding: 15px 20px;
        }
        
        .content-wrapper {
            padding: 15px 20px;
        }
        
        .compact-info {
            margin: 10px 0;
            padding: 12px;
        }
        
        .info-grid {
            grid-template-columns: 1fr;
            gap: 10px;
        }
    }
    
    /* 动画效果 */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .main-content {
        animation: fadeIn 0.6s ease-out;
    }
    
    /* 加载动画 */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .loading {
        animation: pulse 1.5s infinite;
    }
    </style>
    """
    
    with gr.Column(elem_classes="main-content"):
        # 添加CSS样式 - 只针对报告模块
        gr.HTML(css)
        
        # 美化的标题区域
        gr.HTML("""
        <div class="header-section">
            <h2>📊 FastChat 投票分析报告</h2>
            <p>生成完整的投票分析报告，包含 ELO 排名、胜率统计和可视化图表</p>
        </div>
        """)
        
        # 按钮行 - 添加样式类
        with gr.Row(elem_classes="button-row"):
            generate_btn = gr.Button("📊 生成投票分析报告", variant="primary", size="lg")
            refresh_btn = gr.Button("🔄 刷新报告", variant="secondary")
            force_refresh_btn = gr.Button("🔄 强制刷新最新数据", variant="secondary")
        
        # 内容包装器
        with gr.Column(elem_classes="content-wrapper"):
            # 状态信息
            with gr.Row():
                status_box = gr.Textbox(
                    label="", 
                    value="点击按钮生成 FastChat 投票分析报告", 
                    interactive=False,
                    max_lines=1,
                    show_label=False,
                    container=False,
                    elem_classes="status-info"
                )
            
            # 使用说明 - 紧凑版本
            gr.HTML("""
            <div class="compact-info">
                <div class="info-grid">
                    <div><strong>📖 使用说明：</strong></div>
                    <div>
                        <strong>生成投票分析报告</strong>：生成标准的累积投票分析报告 |
                        <strong>刷新报告</strong>：刷新显示最新已生成的报告 |
                        <strong>强制刷新最新数据</strong>：强制重新分析所有数据，确保包含最新的投票信息（推荐用于获取实时数据）
                    </div>
                </div>
            </div>
            """)
            
            # HTML报告显示区域
            html_report = gr.HTML(
                label="", 
                value="<div style='text-align: center; color: #f1f5f9; padding: 50px; background: linear-gradient(135deg, #475569 0%, #334155 100%); border-radius: 12px; border: 2px dashed #64748b;'><h3 style='margin: 0; color: #ffffff;'>📊 点击上方按钮生成 FastChat 投票分析报告</h3><p style='margin: 10px 0 0 0; opacity: 0.8; color: #cbd5e1;'>报告将在此处显示</p></div>",
                elem_classes="report-container",
                show_label=False
            )
        
        # 绑定事件
        generate_btn.click(
            fn=generate_html_report, 
            outputs=[status_box, html_report]
        )
        
        refresh_btn.click(
            fn=refresh_latest_report,
            outputs=[status_box, html_report]
        )
        
        force_refresh_btn.click(
            fn=generate_html_report_force_refresh,
            outputs=[status_box, html_report]
        )
        
        return [generate_btn, refresh_btn, force_refresh_btn, status_box, html_report]