# FastChat API 启动指南

本指南将帮助您使用API方式启动FastChat，无需本地模型。

## 前置要求

1. 安装 FastChat：
```bash
pip install fschat[model_worker,webui]
```

2. 准备API密钥：
   - OpenAI API Key (用于 GPT-4, GPT-3.5-turbo)
   - Anthropic API Key (用于 Claude)
   - Google API Key (用于 Gemini)

## 配置步骤

### 1. 配置API密钥

编辑 `api_endpoint.json` 文件，将您的API密钥替换到相应位置：

```json
{
    "gpt-4o-2024-05-13": {
        "model_name": "gpt-4o-2024-05-13",
        "api_base": "https://api.openai.com/v1",
        "api_type": "openai",
        "api_key": "sk-your-openai-api-key-here",
        "anony_only": false,
        "recommended_config": {
            "temperature": 0.7,
            "top_p": 1.0
        },
        "text-arena": true,
        "vision-arena": false
    }
}
```

### 2. 支持的API类型

- **OpenAI**: `"api_type": "openai"`
- **Anthropic**: `"api_type": "anthropic_message"`
- **Google Gemini**: `"api_type": "gemini"`
- **Mistral**: `"api_type": "mistral"`

## 启动方式

### 方式1: 使用Python脚本（推荐）

```bash
python3 start_simple.py
```

### 方式2: 使用Shell脚本

```bash
./start_fastchat_api.sh
```

### 方式3: 手动启动

1. 启动控制器：
```bash
python3 -m fastchat.serve.controller
```

2. 在另一个终端启动Web服务器：
```bash
python3 -m fastchat.serve.gradio_web_server_multi \
    --host 0.0.0.0 \
    --port 7860 \
    --share \
    --register-api-endpoint-file api_endpoint.json \
    --vision-arena
```

## 访问服务

启动成功后，您可以通过以下地址访问：

- **本地访问**: http://localhost:7860
- **公网访问**: 程序会自动生成一个公网链接

## 功能特性

- ✅ 支持多种大模型API (OpenAI, Anthropic, Gemini, Mistral)
- ✅ 文本对话功能
- ✅ 视觉对话功能 (Vision Arena)
- ✅ 模型对比功能 (Chatbot Arena)
- ✅ 公网分享功能

## 故障排除

### 1. 依赖问题
如果遇到依赖问题，请确保安装了正确的包：
```bash
pip install fschat[model_worker,webui]
```

### 2. API密钥问题
- 确保API密钥正确且有效
- 检查API密钥是否有足够的配额
- 确保网络连接正常

### 3. 端口占用
如果7860端口被占用，可以修改端口：
```bash
python3 -m fastchat.serve.gradio_web_server_multi --port 7861
```

### 4. 模型不显示
如果模型列表为空，请检查：
- API配置文件格式是否正确
- API密钥是否有效
- 网络连接是否正常

## 高级配置

### 自定义模型配置

您可以在 `api_endpoint.json` 中添加更多模型：

```json
{
    "your-custom-model": {
        "model_name": "your-custom-model",
        "api_type": "openai",
        "api_base": "https://your-api-endpoint.com/v1",
        "api_key": "your-api-key",
        "anony_only": false,
        "recommended_config": {
            "temperature": 0.7,
            "top_p": 1.0
        },
        "text-arena": true,
        "vision-arena": false
    }
}
```

### 环境变量配置

您也可以使用环境变量来配置API密钥：

```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"
```

然后在配置文件中使用环境变量：

```json
{
    "gpt-4": {
        "api_key": "${OPENAI_API_KEY}"
    }
}
```

## 停止服务

- 按 `Ctrl+C` 停止服务
- 或者找到进程ID并终止：
```bash
pkill -f "fastchat.serve"
``` 