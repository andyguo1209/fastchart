# FastChat 投票统计工具使用指南

本工具提供了多种方式来统计和分析 FastChat Arena 模式的投票结果。

## 工具概览

### 1. 基础投票统计 (`vote_analysis.py`)
- 统计投票类型分布
- 分析模型胜负记录
- 计算胜率排名
- 时间分析

### 2. ELO评分分析 (`elo_analysis_simple.py`)
- 基于ELO算法计算模型评分
- 生成模型排名
- 支持自定义K因子
- 导出详细统计

### 3. 官方高级工具
FastChat还提供了更高级的分析工具：
- `fastchat/serve/monitor/elo_analysis.py` - 完整的ELO分析
- `fastchat/serve/monitor/basic_stats.py` - 基础统计
- `fastchat/serve/monitor/clean_battle_data.py` - 数据清洗

## 使用方法

### 基础投票统计

```bash
# 使用默认日志文件
python vote_analysis.py

# 指定日志文件
python vote_analysis.py --log-file /path/to/chat.log

# 导出结果到CSV
python vote_analysis.py --export --output vote_results.csv
```

### ELO评分分析

```bash
# 使用默认设置
python elo_analysis_simple.py

# 自定义K因子
python elo_analysis_simple.py --k-factor 24

# 导出结果
python elo_analysis_simple.py --export --output elo_results.csv
```

### 官方高级分析

```bash
# 进入FastChat目录
cd fastchat/serve/monitor

# 运行ELO分析
python elo_analysis.py --clean-battle-file battles.json --rating-system bt

# 生成基础统计
python basic_stats.py --max-num-files 100
```

## 日志文件位置

FastChat的投票日志通常保存在：
- `logs/chat.log` - 默认位置
- `logs/chat_vision.log` - 视觉模型日志
- `logs/chat_vision_csam.log` - 视觉模型CSAM日志

## 投票类型说明

- `leftvote` - 选择左侧模型（Model A）
- `rightvote` - 选择右侧模型（Model B）
- `tievote` - 平局
- `bothbad_vote` - 两个都不好

## 输出示例

### 基础统计输出
```
=== 投票统计概览 ===
总投票数: 150
投票类型分布:
  leftvote: 65 (43.3%)
  rightvote: 70 (46.7%)
  tievote: 10 (6.7%)
  bothbad_vote: 5 (3.3%)

=== 模型表现统计 ===
模型名称            总对战   胜利   失败   平局   胜率   平局率
--------------------------------------------------------------------------------
HKGAI-V1-Thinking  80      45     30     5     56.3%  6.3%
HKGAI-V1           70      40     25     5     57.1%  7.1%
```

### ELO排名输出
```
=== ELO排名结果 ===
排名 模型名称             ELO评分  总对战 胜利 失败 平局 胜率  
----------------------------------------------------------------------
1    HKGAI-V1-Thinking   1050.2   80     45   30   5   56.3%
2    HKGAI-V1            1045.8   70     40   25   5   57.1%
```

## 高级功能

### 实时监控
FastChat Web界面提供了实时监控功能：
- 访问 `http://localhost:8000` 
- 查看 "Monitor" 标签页
- 实时查看投票统计和排名

### 数据导出
所有工具都支持CSV格式导出，可以进一步在Excel或其他工具中分析。

### 自定义分析
你可以修改脚本来：
- 添加更多统计指标
- 自定义评分算法
- 生成可视化图表
- 设置告警阈值

## 注意事项

1. **数据完整性**: 确保日志文件完整，避免数据丢失
2. **时间同步**: 多服务器部署时注意时间同步
3. **数据备份**: 定期备份投票数据
4. **隐私保护**: 投票数据可能包含用户信息，注意隐私保护

## 故障排除

### 常见问题

1. **找不到日志文件**
   - 检查FastChat是否正在运行
   - 确认日志文件路径正确
   - 检查文件权限

2. **数据为空**
   - 确认有用户进行了投票
   - 检查日志格式是否正确
   - 验证时间范围

3. **ELO评分异常**
   - 检查对战数据完整性
   - 调整K因子参数
   - 验证胜负判定逻辑

### 调试技巧

```bash
# 查看日志文件内容
head -20 logs/chat.log

# 统计投票数量
grep -c "leftvote\|rightvote\|tievote\|bothbad_vote" logs/chat.log

# 查看最新投票
tail -10 logs/chat.log
```

## 扩展开发

如果需要自定义分析功能，可以参考：
- `fastchat/serve/monitor/` 目录下的官方工具
- 修改现有脚本添加新功能
- 集成第三方分析库（如matplotlib、seaborn等）

## 联系支持

如有问题或建议，请：
1. 查看FastChat官方文档
2. 提交Issue到GitHub仓库
3. 参考社区讨论 