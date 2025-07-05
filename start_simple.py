#!/usr/bin/env python3
"""
FastChat API 启动脚本
使用API方式启动大模型，不需要本地模型
"""

import subprocess
import sys
import time
import signal
import os

def check_dependencies():
    """检查依赖"""
    try:
        import fastchat
        print("✓ FastChat 已安装")
    except ImportError:
        print("✗ 错误: 未安装 FastChat")
        print("请先运行: pip install fschat[model_worker,webui]")
        sys.exit(1)

def check_config():
    """检查配置文件"""
    if not os.path.exists("api_endpoint.json"):
        print("✗ 错误: 未找到 api_endpoint.json 配置文件")
        print("请先配置您的API密钥")
        sys.exit(1)
    print("✓ API 配置文件已找到")

def start_controller():
    """启动控制器"""
    print("启动 Controller...")
    controller_process = subprocess.Popen([
        sys.executable, "-m", "fastchat.serve.controller"
    ])
    time.sleep(3)  # 等待控制器启动
    return controller_process

def start_web_server():
    """启动Web服务器"""
    print("启动 Gradio Web 服务器...")
    print("访问地址: http://localhost:7860")
    print("按 Ctrl+C 停止服务")
    
    web_server_process = subprocess.run([
        sys.executable, "-m", "fastchat.serve.gradio_web_server_multi",
        "--host", "0.0.0.0",
        "--port", "7860",
        "--share",
        "--register-api-endpoint-file", "api_endpoint.json",
        "--vision-arena"
    ])
    return web_server_process

def main():
    print("=== FastChat API 启动脚本 ===")
    print("使用API方式启动大模型，不需要本地模型")
    print()
    
    # 检查依赖和配置
    check_dependencies()
    check_config()
    
    # 启动控制器
    controller_process = start_controller()
    
    try:
        # 启动Web服务器
        start_web_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    finally:
        # 清理进程
        if controller_process.poll() is None:
            controller_process.terminate()
            controller_process.wait()
        print("服务已关闭")

if __name__ == "__main__":
    main() 