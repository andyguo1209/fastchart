#!/usr/bin/env python3
"""
使用官方FastChat工具的自动化分析脚本
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import gradio as gr

def setup_log_directory(log_file):
    """设置日志目录结构"""
    print("📁 设置日志目录结构...")
    
    # 创建logs目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 复制日志文件到logs目录
    log_filename = Path(log_file).name
    dest_path = logs_dir / log_filename
    
    if not dest_path.exists():
        shutil.copy2(log_file, dest_path)
        print(f"✅ 日志文件已复制到: {dest_path}")
    else:
        print(f"✅ 日志文件已存在: {dest_path}")
    
    return dest_path

def run_clean_battle_data():
    """运行官方数据清理工具"""
    print("\n🧹 运行官方数据清理工具...")
    
    try:
        cmd = "python -m fastchat.serve.monitor.clean_battle_data --mode simple"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ 数据清理完成")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 数据清理失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def run_elo_analysis():
    """运行官方ELO分析工具"""
    print("\n📊 运行官方ELO分析工具...")
    
    try:
        # 查找清理后的数据文件
        clean_files = list(Path(".").glob("clean_battle_*.json"))
        if not clean_files:
            print("❌ 未找到清理后的数据文件")
            return False
        
        latest_file = max(clean_files, key=lambda x: x.stat().st_mtime)
        print(f"📄 使用数据文件: {latest_file}")
        
        # 运行ELO分析
        cmd = f"python -m fastchat.serve.monitor.elo_analysis --input-file {latest_file}"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ ELO分析完成")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ ELO分析失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def run_basic_stats():
    """运行基础统计工具"""
    print("\n📈 运行基础统计工具...")
    
    try:
        cmd = "python -m fastchat.serve.monitor.basic_stats"
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ 基础统计完成")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 基础统计失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False

def start_official_monitor(port=8080):
    """启动官方监控界面"""
    print(f"\n🌐 启动官方监控界面 (端口: {port})...")
    
    try:
        cmd = f"python -m fastchat.serve.monitor.monitor --port {port}"
        print(f"🚀 启动命令: {cmd}")
        print(f"📱 请在浏览器中访问: http://localhost:{port}")
        print("⏹️  按 Ctrl+C 停止服务器")
        
        subprocess.run(cmd, shell=True)
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 启动服务器失败: {e}")

def create_summary_report():
    """创建分析总结报告"""
    print("\n📋 创建分析总结报告...")
    
    report_content = f"""# FastChat 投票分析报告

## 分析时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 使用的工具
1. **数据清理**: `fastchat.serve.monitor.clean_battle_data`
2. **ELO分析**: `fastchat.serve.monitor.elo_analysis`
3. **基础统计**: `fastchat.serve.monitor.basic_stats`
4. **Web监控**: `fastchat.serve.monitor.monitor`

## 生成的文件
- `clean_battle_*.json`: 清理后的对战数据
- `elo_results_*.json`: ELO分析结果
- 各种统计图表和可视化

## 使用方法

### 1. 数据清理
```bash
python -m fastchat.serve.monitor.clean_battle_data --mode simple
```

### 2. ELO分析
```bash
python -m fastchat.serve.monitor.elo_analysis --input-file clean_battle_YYYYMMDD.json
```

### 3. 基础统计
```bash
python -m fastchat.serve.monitor.basic_stats
```

### 4. Web监控界面
```bash
python -m fastchat.serve.monitor.monitor --port 8080
```

## 注意事项
- 确保日志文件在 `logs/` 目录中
- 官方工具会自动处理数据格式和统计
- Web界面提供实时监控和可视化
- 支持多种分析模式和过滤选项

## 官方文档
更多详细信息请参考 FastChat 官方文档中的 monitor 部分。
"""
    
    with open("analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print("✅ 分析报告已创建: analysis_report.md")

def main():
    parser = argparse.ArgumentParser(description="使用官方FastChat工具的自动化分析脚本")
    parser.add_argument("--log-file", type=str, required=True, help="投票日志文件路径")
    parser.add_argument("--port", type=int, default=8080, help="Web服务器端口 (默认: 8080)")
    parser.add_argument("--no-web", action="store_true", help="只分析数据，不启动Web服务器")
    parser.add_argument("--skip-clean", action="store_true", help="跳过数据清理步骤")
    
    args = parser.parse_args()
    
    # 检查文件是否存在
    if not os.path.exists(args.log_file):
        print(f"❌ 错误: 日志文件不存在: {args.log_file}")
        sys.exit(1)
    
    print("🚀 FastChat 官方工具自动化分析脚本")
    print("=" * 50)
    
    # 设置日志目录
    log_path = setup_log_directory(args.log_file)
    
    # 数据清理
    if not args.skip_clean:
        if not run_clean_battle_data():
            print("❌ 数据清理失败，退出程序")
            sys.exit(1)
    else:
        print("⏭️  跳过数据清理步骤")
    
    # ELO分析
    if not run_elo_analysis():
        print("❌ ELO分析失败，退出程序")
        sys.exit(1)
    
    # 基础统计
    if not run_basic_stats():
        print("❌ 基础统计失败，退出程序")
        sys.exit(1)
    
    # 创建总结报告
    create_summary_report()
    
    # 启动Web服务器
    if not args.no_web:
        start_official_monitor(args.port)
    else:
        print("\n✅ 分析完成！")
        print("📊 生成的文件:")
        print("  - clean_battle_*.json (清理后的数据)")
        print("  - elo_results_*.json (ELO分析结果)")
        print("  - analysis_report.md (分析报告)")
        print("\n🌐 要启动官方Web监控界面，请运行:")
        print(f"   python -m fastchat.serve.monitor.monitor --port {args.port}")
        print(f"   然后在浏览器中访问: http://localhost:{args.port}")

    # 添加 Gradio 的 Markdown 组件
    gr.Markdown(
        """
        <div style="background:#667eea;color:white;padding:24px 10px 16px 10px;text-align:center;">
          <h1 style="font-size:2em;margin-bottom:8px;">FastChat 投票分析报告</h1>
          <div style="font-size:1.1em;opacity:0.92;">模型对战结果统计与ELO排名分析</div>
          <div style="font-size:0.95em;margin-top:10px;opacity:0.8;">数据来源: FastChat Arena 投票系统</div>
          <a href="reports/2025-06-27_091319/report.html" target="_blank" style="display:inline-block;margin-top:18px;padding:8px 22px;background:#ff9800;color:white;font-weight:bold;border-radius:6px;text-decoration:none;">�� 查看完整报告</a>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:18px 0;">
          <div style="background:#764ba2;color:white;padding:12px 18px;border-radius:8px;min-width:90px;text-align:center;">
            <div style="font-size:1.5em;font-weight:bold;">2</div>
            <div style="font-size:1em;opacity:0.92;">总投票数</div>
          </div>
          <div style="background:#764ba2;color:white;padding:12px 18px;border-radius:8px;min-width:90px;text-align:center;">
            <div style="font-size:1.5em;font-weight:bold;">2</div>
            <div style="font-size:1em;opacity:0.92;">参与模型数</div>
          </div>
          <div style="background:#764ba2;color:white;padding:12px 18px;border-radius:8px;min-width:90px;text-align:center;">
            <div style="font-size:1.5em;font-weight:bold;">1</div>
            <div style="font-size:1em;opacity:0.92;">有效对战数</div>
          </div>
          <div style="background:#764ba2;color:white;padding:12px 18px;border-radius:8px;min-width:90px;text-align:center;">
            <div style="font-size:1.5em;font-weight:bold;">2025-06-27</div>
            <div style="font-size:1em;opacity:0.92;">分析日期</div>
          </div>
        </div>
        """
    )

if __name__ == "__main__":
    main() 