#!/bin/bash

# FastChat API 启动脚本
# 使用API方式启动大模型，不需要本地模型

echo "正在启动 FastChat API 服务..."

# 函数：停止现有的 FastChat 进程
stop_fastchat_processes() {
    echo "检查并停止现有的 FastChat 进程..."
    
    # 查找并停止 fastchat.serve.controller 进程
    CONTROLLER_PIDS=$(pgrep -f "fastchat.serve.controller")
    if [ ! -z "$CONTROLLER_PIDS" ]; then
        echo "发现现有的 Controller 进程: $CONTROLLER_PIDS"
        echo "正在停止 Controller 进程..."
        kill $CONTROLLER_PIDS 2>/dev/null
        sleep 2
        # 如果进程仍在运行，强制杀死
        kill -9 $CONTROLLER_PIDS 2>/dev/null
    fi
    
    # 查找并停止 fastchat.serve.gradio_web_server_multi 进程
    GRADIO_PIDS=$(pgrep -f "fastchat.serve.gradio_web_server_multi")
    if [ ! -z "$GRADIO_PIDS" ]; then
        echo "发现现有的 Gradio Web 服务器进程: $GRADIO_PIDS"
        echo "正在停止 Gradio Web 服务器进程..."
        kill $GRADIO_PIDS 2>/dev/null
        sleep 2
        # 如果进程仍在运行，强制杀死
        kill -9 $GRADIO_PIDS 2>/dev/null
    fi
    
    # 检查端口 7860 是否被占用
    PORT_PID=$(lsof -ti:7860 2>/dev/null)
    if [ ! -z "$PORT_PID" ]; then
        echo "发现端口 7860 被进程 $PORT_PID 占用，正在停止..."
        kill $PORT_PID 2>/dev/null
        sleep 2
        kill -9 $PORT_PID 2>/dev/null
    fi
    
    echo "现有进程清理完成"
}

# 停止现有进程
stop_fastchat_processes

# 检查是否安装了必要的依赖
echo "检查依赖..."
python -c "import fastchat" 2>/dev/null || {
    echo "错误: 未安装 FastChat，请先运行: pip install fschat[model_worker,webui]"
    exit 1
}

# 检查API配置文件是否存在
if [ ! -f "api_endpoint.json" ]; then
    echo "错误: 未找到 api_endpoint.json 配置文件"
    echo "请先配置您的API密钥"
    exit 1
fi

echo "启动 Controller..."
# 启动控制器（后台运行）
python -m fastchat.serve.controller &
CONTROLLER_PID=$!
echo "Controller 已启动 (PID: $CONTROLLER_PID)"

# 等待控制器启动
sleep 3

echo "启动 Gradio Web 服务器..."
# 启动 Gradio Web 服务器（前台运行，这样可以看到日志）
python -m fastchat.serve.gradio_web_server_multi \
    --host 0.0.0.0 \
    --port 7860 \
    --share \
    --register-api-endpoint-file api_endpoint.json \
    --vision-arena

# 当用户按 Ctrl+C 时，清理进程
trap "echo '正在关闭服务...'; kill $CONTROLLER_PID 2>/dev/null; exit" INT 

mkdir -p static/reports
cp reports/*/report.html static/reports/ 2>/dev/null
# 或者重命名带日期
for d in reports/*; do
  if [ -f "$d/report.html" ]; then
    cp "$d/report.html" "static/reports/$(basename $d)_report.html"
  fi
done 2>/dev/null 