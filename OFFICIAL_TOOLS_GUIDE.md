# FastChat 官方统计分析工具使用指南

FastChat 提供了完整的官方工具链来进行投票统计分析，包括数据清洗、ELO评分计算、基础统计等。

## 工具概览

### 核心工具
1. **`clean_battle_data.py`** - 数据清洗和预处理
2. **`elo_analysis.py`** - ELO评分和排名分析
3. **`basic_stats.py`** - 基础统计信息
4. **`monitor.py`** - 实时监控和可视化

## 完整分析流程

### 第一步：数据清洗

```bash
cd fastchat/serve/monitor

# 基础清洗
python clean_battle_data.py --max-num-files 100 --mode simple

# 排除测试模型
python clean_battle_data.py --max-num-files 100 --exclude-model-names "test-*"

# IP脱敏
python clean_battle_data.py --max-num-files 100 --sanitize-ip

# 使用IP黑名单
python clean_battle_data.py --max-num-files 100 --ban-ip-file ban_ips.json
```

**参数说明：**
- `--max-num-files`: 处理的最大日志文件数量
- `--mode`: 输出模式 (simple/conv_release)
- `--exclude-model-names`: 排除的模型名称
- `--sanitize-ip`: 是否脱敏IP地址
- `--ban-ip-file`: IP黑名单文件

**输出文件：**
- `clean_battle_YYYYMMDD.json` - 清洗后的对战数据

### 第二步：ELO评分分析

```bash
# 使用清洗后的数据文件
python elo_analysis.py --clean-battle-file clean_battle_20241226.json

# 使用原始日志文件
python elo_analysis.py --max-num-files 100

# 自定义评分系统
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --rating-system elo

# 排除平局
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --exclude-tie

# 限制用户每日投票数
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --daily-vote-per-user 10

# 异常检测
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --run-outlier-detect

# 样式控制分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --style-control

# 多类别分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --category full long chinese english
```

**参数说明：**
- `--clean-battle-file`: 清洗后的对战数据文件
- `--max-num-files`: 直接处理日志文件数量
- `--rating-system`: 评分系统 (bt/elo)
- `--exclude-tie`: 排除平局投票
- `--daily-vote-per-user`: 限制用户每日投票数
- `--run-outlier-detect`: 运行异常检测
- `--style-control`: 启用样式控制分析
- `--category`: 分析类别 (full/long/chinese/english)
- `--num-bootstrap`: Bootstrap采样次数 (默认100)
- `--scale`: 图表缩放比例 (默认1)

**输出文件：**
- `elo_results_YYYYMMDD.pkl` - ELO分析结果

### 第三步：基础统计

```bash
# 基础统计信息
python basic_stats.py --max-num-files 100
```

**输出内容：**
- 动作类型统计
- 模型调用统计
- 匿名投票统计
- 24小时聊天统计

## 高级分析功能

### 1. 多维度分析

```bash
# 按语言分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --langs Chinese English

# 排除未知语言
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --exclude-unknown-lang

# 长对话分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --category long
```

### 2. 异常检测

```bash
# 启用异常检测
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --run-outlier-detect
```

异常检测会识别：
- 投票模式异常的IP
- 可能的机器人投票
- 数据质量问题

### 3. 样式控制分析

```bash
# 启用样式控制
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --style-control
```

样式控制分析会考虑：
- 回复长度
- Markdown使用
- 格式偏好
- 其他可能影响评分的因素

## 输出结果解读

### ELO分析输出

```
# Results for full conversations
# Online Elo
 1, HKGAI-V1-Thinking        , 1050
 2, HKGAI-V1                 , 1045
 3, gpt-3.5-turbo            , 1000
# Median
 1, HKGAI-V1-Thinking        , 1052
 2, HKGAI-V1                 , 1048
 3, gpt-3.5-turbo            , 1000
last update : 2024-12-26 10:30:00 PST
```

### 基础统计输出

```
| type | All | Last Day | Last Hour |
|------|-----|----------|-----------|
| chat | 1500| 120      | 5         |
| leftvote | 750 | 60 | 2 |
| rightvote | 720 | 58 | 3 |
| tievote | 25 | 2 | 0 |
| bothbad_vote | 5 | 0 | 0 |
```

## 实时监控

### Web界面监控

```bash
# 启动带监控的FastChat
python -m fastchat.serve.gradio_web_server_multi --controller-url http://localhost:21001 --port 8000
```

访问 `http://localhost:8000` 查看：
- 实时投票统计
- 模型排名
- 可视化图表
- 系统状态

### 监控数据更新

```bash
# 定期更新监控数据
python monitor.py --elo-results-file elo_results_20241226.pkl
```

## 数据文件格式

### 清洗后的对战数据格式

```json
{
  "question_id": "conv_id",
  "model_a": "HKGAI-V1-Thinking",
  "model_b": "HKGAI-V1",
  "winner": "model_a",
  "judge": "arena_user_ip_hash",
  "conversation_a": [...],
  "conversation_b": [...],
  "turn": 3,
  "anony": true,
  "language": "Chinese",
  "tstamp": 1703610000.0
}
```

### ELO结果文件格式

```python
{
  "full": {
    "elo_rating_final": {"HKGAI-V1-Thinking": 1052, "HKGAI-V1": 1048},
    "leaderboard_table": "markdown_table",
    "win_fraction_heatmap": "plotly_figure",
    "bootstrap_df": "pandas_dataframe",
    "last_updated_datetime": "2024-12-26 10:30:00 PST"
  }
}
```

## 最佳实践

### 1. 数据质量保证

```bash
# 定期清洗数据
python clean_battle_data.py --max-num-files 100 --sanitize-ip --exclude-model-names "test-*"

# 运行异常检测
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --run-outlier-detect
```

### 2. 分析策略

```bash
# 多维度分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json \
  --category full long chinese english \
  --rating-system bt \
  --style-control \
  --num-bootstrap 200
```

### 3. 结果验证

```bash
# 交叉验证
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --rating-system elo
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --rating-system bt

# 时间窗口分析
python elo_analysis.py --clean-battle-file clean_battle_20241226.json --daily-vote-per-user 5
```

## 故障排除

### 常见问题

1. **内存不足**
   ```bash
   # 减少处理文件数量
   python clean_battle_data.py --max-num-files 50
   
   # 减少Bootstrap次数
   python elo_analysis.py --num-bootstrap 50
   ```

2. **处理速度慢**
   ```bash
   # 增加CPU核心数
   python elo_analysis.py --num-cpu 16
   ```

3. **数据不完整**
   ```bash
   # 检查日志文件
   ls -la logs/
   
   # 验证数据格式
   head -5 logs/chat.log
   ```

### 调试技巧

```bash
# 查看处理进度
python clean_battle_data.py --max-num-files 10

# 检查中间结果
python -c "import pickle; data=pickle.load(open('elo_results_20241226.pkl','rb')); print(data.keys())"

# 验证数据完整性
python -c "import json; data=json.load(open('clean_battle_20241226.json')); print(len(data))"
```

## 自动化脚本

### 每日分析脚本

```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
cd fastchat/serve/monitor

# 数据清洗
python clean_battle_data.py --max-num-files 100 --sanitize-ip

# ELO分析
python elo_analysis.py --clean-battle-file clean_battle_${DATE}.json --style-control

echo "Analysis completed for ${DATE}"
```

### 监控脚本

```bash
#!/bin/bash
# monitor_loop.sh

while true; do
    python basic_stats.py --max-num-files 10
    sleep 300  # 每5分钟更新一次
done
```

## 扩展开发

### 自定义分析

```python
# 自定义分析脚本示例
import pickle
import pandas as pd

# 加载ELO结果
with open('elo_results_20241226.pkl', 'rb') as f:
    results = pickle.load(f)

# 提取数据
elo_ratings = results['full']['elo_rating_final']
bootstrap_df = results['full']['bootstrap_df']

# 自定义分析
print("Top 5 Models:")
for i, (model, rating) in enumerate(sorted(elo_ratings.items(), key=lambda x: x[1], reverse=True)[:5]):
    print(f"{i+1}. {model}: {rating:.1f}")
```

### 集成第三方工具

```python
# 集成matplotlib可视化
import matplotlib.pyplot as plt

# 绘制ELO评分分布
plt.figure(figsize=(10, 6))
plt.hist(bootstrap_df.values.flatten(), bins=30, alpha=0.7)
plt.title('ELO Rating Distribution')
plt.xlabel('ELO Rating')
plt.ylabel('Frequency')
plt.savefig('elo_distribution.png')
```

## 总结

FastChat官方工具提供了完整的投票统计分析解决方案：

1. **数据清洗** - 确保数据质量
2. **ELO分析** - 科学评分排名
3. **基础统计** - 实时监控
4. **可视化** - 直观展示结果

通过这些工具，你可以全面分析你的 `HKGAI-V1-Thinking` 和 `HKGAI-V1` 模型在 Arena 模式中的表现，并获得科学的排名结果。 