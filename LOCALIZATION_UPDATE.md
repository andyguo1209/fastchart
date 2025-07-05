# FastChat 报告生成脚本本地化更新

## 更新概述

本次更新为 `generate_report.py` 脚本添加了完整的多语言支持功能，现在支持中文和英文两种语言。

## 新增功能

### 1. 自动语言检测
- 脚本会自动检测系统语言设置
- 支持中文（zh）和英文（en）
- 默认语言为中文

### 2. 完整的文本本地化
- 所有用户界面文本都已本地化
- 包括命令行输出、HTML报告内容、摘要报告等
- 支持动态文本格式化

### 3. 多语言翻译字典
- 完整的中英文翻译对照
- 包含60+个翻译键值对
- 支持扩展更多语言

## 技术实现

### 语言检测函数
```python
def get_current_language():
    """获取当前系统语言"""
    try:
        import locale
        lang = locale.getdefaultlocale()[0]
        if lang and lang.startswith('zh'):
            return 'zh'
        return 'en'
    except:
        return 'zh'  # 默认中文
```

### 翻译函数
```python
def t(key):
    """获取翻译文本"""
    lang = get_current_language()
    return translations.get(lang, translations['zh']).get(key, key)
```

### 使用方式
```python
# 替换前
print("📊 开始分析投票数据")

# 替换后
print(t('analyzing_vote_data').format(log_file))
```

## 支持的语言

### 中文 (zh)
- 简体中文界面
- 完整的中文术语翻译
- 适合中文用户使用

### 英文 (en)
- 英文界面
- 专业术语英文翻译
- 国际化标准

## 主要更新内容

### 1. 命令行输出本地化
- 所有 print 语句使用 t() 函数
- 支持动态参数格式化
- 错误信息本地化

### 2. HTML报告本地化
- 报告标题和页面元素
- 表格标题和列名
- 图表标签和说明文字
- 页脚信息

### 3. 摘要报告本地化
- Markdown格式报告
- 章节标题和内容
- 统计数据标签

## 兼容性

### 向后兼容
- 完全兼容现有功能
- 不影响现有脚本调用方式
- 保持原有的输出格式

### 系统要求
- Python 3.6+
- 支持 locale 模块
- UTF-8 编码支持

## 使用示例

### 中文环境
```bash
# 系统语言为中文时
python generate_report.py --help
# 输出: FastChat 一键报告生成脚本

python generate_report.py --log-file data.json
# 输出: 🚀 FastChat 一键报告生成脚本
#       📊 开始分析投票数据: data.json
```

### 英文环境
```bash
# 系统语言为英文时
python generate_report.py --help
# 输出: FastChat One-Click Report Generation Script

python generate_report.py --log-file data.json
# 输出: 🚀 FastChat One-Click Report Generation Script
#       📊 Starting vote data analysis: data.json
```

## 扩展支持

### 添加新语言
1. 在 `translations` 字典中添加新语言代码
2. 翻译所有键值对
3. 更新 `get_current_language()` 函数

### 添加新文本
1. 在两种语言的翻译字典中添加键值对
2. 使用 `t('new_key')` 调用

## 测试验证

本地化功能已通过以下测试：
- ✅ 语言检测功能
- ✅ 翻译字典完整性
- ✅ 格式化功能
- ✅ 错误处理
- ✅ 脚本正常运行

## 文件结构

```
FastChat/
├── generate_report.py          # 主脚本（已更新）
├── LOCALIZATION_UPDATE.md      # 本文档
├── vote_analysis.py           # 投票分析脚本
├── elo_analysis_simple.py     # ELO分析脚本
└── README.md                  # 项目说明
```

## 注意事项

1. **字符编码**: 确保终端支持UTF-8编码显示emoji和中文
2. **系统语言**: 脚本会自动检测系统语言，无需手动设置
3. **回退机制**: 如果翻译缺失，会返回原始键值作为回退
4. **性能影响**: 本地化功能对性能影响极小

## 更新历史

- **v1.1.0** (2024-12-19): 添加完整的中英文本地化支持
- **v1.0.0**: 初始版本，仅支持中文

---

*此更新提升了脚本的国际化水平，使其能够更好地服务于不同语言背景的用户。* 