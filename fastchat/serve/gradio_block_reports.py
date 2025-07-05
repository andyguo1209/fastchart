"""
Simplified report display component for FastChat Web UI.
Displays complete HTML reports with proper chart support.
"""

import subprocess
import os
import gradio as gr
from pathlib import Path
import re

def run_generate_report():
    """运行generate_report.py脚本生成报告"""
    try:
        # 获取项目根目录路径
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent  # 从 fastchat/serve/ 回到项目根目录
        
        print(f"项目根目录: {project_root}")
        print(f"当前工作目录: {os.getcwd()}")
        
        # 运行generate_report.py脚本 - 使用累积分析模式
        result = subprocess.run(['python', 'generate_report.py', '--cumulative'], 
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
                        return f"✅ FastChat 投票分析报告生成成功！已处理累积数据，包含最新投票信息。", str(report_file)
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
                    return f"✅ FastChat 投票分析报告生成成功！已处理累积数据，包含最新投票信息。", str(latest_report)
            
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

def generate_html_report():
    """生成FastChat投票分析HTML报告"""
    # 先运行报告生成
    status_msg, report_path = run_generate_report()
    
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
                    console.log('DOM加载完成，尝试初始化图表');
                    setTimeout(initializeCharts, 500);
                }});
            }} else {{
                console.log('DOM已经加载完成');
                setTimeout(initializeCharts, 500);
            }}
            
            // 窗口加载完成后尝试
            if (document.readyState !== 'complete') {{
                window.addEventListener('load', function() {{
                    console.log('窗口加载完成，尝试初始化图表');
                    setTimeout(initializeCharts, 1000);
                }});
            }} else {{
                console.log('窗口已经加载完成');
                setTimeout(initializeCharts, 1000);
            }}
            
            // 定时尝试
            setTimeout(initializeCharts, 1500);
            setTimeout(initializeCharts, 2500);
            setTimeout(initializeCharts, 4000);
        }}
        
        // 开始初始化
        startInitialization();
    </script>
</body>'''
            
            # 替换</body>标签
            html_content = html_content.replace('</body>', force_init_script)
            
            return status_msg, html_content
        except Exception as e:
            return f"❌ 读取HTML文件失败: {str(e)}", "<p>无法加载报告</p>"
    else:
        return status_msg, "<p>无法生成报告</p>"

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
                    console.log('DOM加载完成，尝试初始化图表');
                    setTimeout(initializeCharts, 500);
                }});
            }} else {{
                console.log('DOM已经加载完成');
                setTimeout(initializeCharts, 500);
            }}
            
            // 窗口加载完成后尝试
            if (document.readyState !== 'complete') {{
                window.addEventListener('load', function() {{
                    console.log('窗口加载完成，尝试初始化图表');
                    setTimeout(initializeCharts, 1000);
                }});
            }} else {{
                console.log('窗口已经加载完成');
                setTimeout(initializeCharts, 1000);
            }}
            
            // 定时尝试
            setTimeout(initializeCharts, 1500);
            setTimeout(initializeCharts, 2500);
            setTimeout(initializeCharts, 4000);
        }}
        
        // 开始初始化
        startInitialization();
    </script>
</body>'''
                    
                    # 替换</body>标签
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
                
                return f"✅ 最新报告已刷新！累积数据已更新，包含最新投票信息。", html_content
        
        return "❌ 未找到任何报告文件", "<p>请先生成报告</p>"
    except Exception as e:
        print(f"刷新报告异常: {str(e)}")
        return f"❌ 刷新报告失败: {str(e)}", "<p>刷新失败</p>"

def build_reports_tab():
    """构建FastChat投票分析报告标签页"""
    
    with gr.Column():
        gr.Markdown("## 📊 FastChat 投票分析报告")
        gr.Markdown("点击按钮生成完整的 FastChat 投票分析报告，包含 ELO 排名、胜率统计和可视化图表。")
        
        with gr.Row():
            generate_btn = gr.Button("📊 生成投票分析报告", variant="primary", size="lg")
            refresh_btn = gr.Button("🔄 刷新报告", variant="secondary")
            status_box = gr.Textbox(
                label="状态", 
                value="点击按钮生成 FastChat 投票分析报告", 
                interactive=False
            )
        
        # HTML报告显示区域
        with gr.Row():
            html_report = gr.HTML(
                label="FastChat 投票分析报告", 
                value="<p style='text-align: center; color: #666; padding: 40px;'>点击上方按钮生成 FastChat 投票分析报告</p>"
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