# 股票板块轮动监控

A股板块资金流向监控工具，支持 Telegram/Notion 多渠道推送，自动生成时间序列图表。

## 功能特性

- 📊 **自动数据获取**: 每日获取A股498个板块资金流数据
- 🔥 **TOP10排名**: 追踪主力净流入最多的板块
- 🔄 **轮动检测**: 识别新进入TOP10的板块（资金流向变化）
- 📱 **多渠道推送**: 支持 Telegram 和 Notion
- 📈 **图表生成**: 自动生成资金流向趋势图、热力图
- 🖼️ **图片嵌入**: 图表直接上传到Notion并嵌入页面（无需第三方图床）
- 🧪 **完整测试**: 70个单元测试，94%代码覆盖率
- ⏰ **定时调度**: 可配置交易日自动运行
- 🐳 **Docker部署**: 一键启动，环境隔离

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd stock-monitor

# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件，选择输出模式：

#### 模式A: Notion（推荐）
```bash
OUTPUT_MODE=notion
NOTION_API_KEY=your_notion_api_key
NOTION_PARENT_PAGE_ID=your_parent_page_id

# 可选：配置Imgur（如需要外部URL访问图片）
# IMGUR_CLIENT_ID=your_imgur_client_id
```

#### 模式B: Telegram
```bash
OUTPUT_MODE=telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

#### 模式C: 双通道
```bash
OUTPUT_MODE=both
# 同时配置Notion和Telegram
```

### 2. 初始化（Notion模式）

```bash
# 初始化Notion数据库
python3 main.py --init-notion

# 将输出的 DATABASE_ID 添加到 .env 文件
```

### 3. 运行

#### 本地运行
```bash
# 立即运行一次（测试）
python3 main.py --run-once

# 启动定时调度（每个交易日15:05自动运行）
python3 main.py
```

#### Docker运行
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f stock-monitor

# 停止
docker-compose down
```

## 项目结构

```
stock-monitor/
├── docker-compose.yml      # Docker Compose配置
├── Dockerfile              # Docker镜像构建
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量模板
├── pytest.ini             # 测试配置
├── README.md              # 本文件
├── NOTION_IMAGE_GUIDE.md  # Notion图片嵌入指南
├── main.py                # 程序入口
├── charts/                # 生成的图表（自动生成）
├── data/                  # 历史数据（自动生成）
├── src/                   # 源代码
│   ├── __init__.py
│   ├── config.py          # 配置管理（Pydantic）
│   ├── data_fetcher.py    # 数据获取（akshare）
│   ├── analyzer.py        # 数据分析（排名、轮动）
│   ├── reporter.py        # 报告生成（Markdown）
│   ├── notifier.py        # Telegram推送
│   ├── notion_writer.py   # Notion页面写入
│   ├── chart_generator.py # 图表生成（matplotlib）
│   ├── image_uploader.py  # 图床上传（Imgur）
│   └── scheduler.py       # 定时调度（APScheduler）
└── tests/                 # 单元测试
    ├── conftest.py
    ├── test_config.py
    ├── test_data_fetcher.py
    ├── test_analyzer.py
    ├── test_reporter.py
    ├── test_notifier.py
    └── test_scheduler.py
```

## 模块说明

### data_fetcher.py
- `DataFetcher.get_sector_flow()`: 获取板块资金流数据
- 使用 akshare 接口
- 自动处理网络异常、空数据

### analyzer.py
- `rank_by_inflow()`: 按净流入排序TOP N
- `detect_rotation()`: 检测新进入TOP10的板块
- `save/load_snapshot()`: 数据持久化（CSV格式）
- `get_last_trading_date()`: 计算上一个交易日

### reporter.py
- `generate_markdown()`: 生成Markdown格式报告
- `generate_summary()`: 生成简短摘要

### notion_writer.py
- `write_report()`: 创建Notion页面，支持嵌入图片（自动上传到Notion）
- `upload_image_to_notion()`: 上传图片到Notion（3步上传流程）
- `_parse_markdown_to_blocks()`: Markdown转Notion blocks
- `create_monitoring_database()`: 创建监控数据库

### chart_generator.py
- `generate_top_sectors_trend()`: TOP板块资金流向趋势图
- `generate_sector_comparison()`: 板块对比图
- `generate_market_heatmap()`: 板块资金流向热力图
- `load_historical_data()`: 加载历史数据

### image_uploader.py
- `upload_to_imgur()`: 上传图片到Imgur获取公开URL
- 支持嵌入Notion页面直接显示

### scheduler.py
- `run_once()`: 单次运行完整流程（7个步骤）
- `start()`: 启动定时调度（APScheduler）
- 支持多种输出模式自动切换

## 运行模式

### 单次运行（测试）
```bash
python3 main.py --run-once
```
执行完整流程一次，立即查看结果。

### 定时调度（生产）
```bash
python3 main.py
```
每个交易日指定时间自动执行，保持后台运行。

### 初始化Notion数据库
```bash
python3 main.py --init-notion
```
在Notion中创建监控记录数据库。

### 测试通知
```bash
# 测试Telegram
python3 main.py --test-notify

# 测试Notion（运行一次即可）
python3 main.py --run-once
```

## 运行流程

```
步骤 1/7: 获取板块资金流数据
步骤 2/7: 计算TOP10排名
步骤 3/7: 保存数据快照
步骤 4/7: 检测板块轮动
步骤 5/7: 生成时间序列图表
步骤 6/7: 上传图表到Notion（自动嵌入页面）
步骤 7/7: 生成并发送报告
```

> 💡 **注意**: 图表现在直接上传到Notion并嵌入页面，无需配置第三方图床（如Imgur）。如果配置了Imgur，将优先使用Imgur URL作为外部图片链接。

## Notion 报告示例

Notion页面包含：

```
📊 板块资金流向监控 - 2026-02-16

🔥 TOP10 板块（按净流入）：
1. 电子 - +24.88亿 (-0.13%)
2. 数字芯片设计 - +19.23亿 (-0.15%)
3. 半导体 - +16.52亿 (+0.12%)
...

🔄 轮动信号（今日新进入TOP10）：
- 半导体（昨日排名：>10）

---
📊 关键指标时间序列图

TOP板块资金流向趋势
[图片直接显示在这里]
```

## 单元测试

```bash
# 运行所有测试
python3 -m pytest tests/ -v

# 生成覆盖率报告
python3 -m pytest tests/ --cov=src --cov-report=term-missing
```

**测试结果**:
- 70个测试用例，全部通过
- 代码覆盖率：94%

## 配置说明

### Notion API Key 获取

1. 访问 https://www.notion.so/my-integrations
2. 创建 Integration，复制 Token
3. 在Notion页面点击 `...` → `Connect to` → 选择你的Integration

### Imgur Client ID 获取（可选，旧版兼容）

**新版已支持直接上传图片到Notion，无需Imgur配置。**

仅当需要外部URL访问图片时才需要配置：

1. 访问 https://api.imgur.com/oauth2/addclient
2. 选择 `OAuth 2 without callback`
3. 复制 Client ID 到 `.env` 文件

详见 [NOTION_IMAGE_GUIDE.md](NOTION_IMAGE_GUIDE.md)（旧版文档）

### Telegram 配置获取

- `TELEGRAM_BOT_TOKEN`: [@BotFather](https://t.me/botfather) 创建bot
- `TELEGRAM_CHAT_ID`: [@userinfobot](https://t.me/userinfobot) 获取

## 数据存储

### 历史数据
- 路径: `data/sector_flow_YYYYMMDD.csv`
- 用途: 轮动检测、趋势分析
- 格式: CSV（UTF-8）

### 图表文件
- 路径: `charts/*.png`
- 内容: 趋势图、热力图
- 自动清理: 保留最近7天

## 依赖项

主要依赖：
- `akshare`: A股数据获取
- `pandas`: 数据处理
- `matplotlib`: 图表生成
- `requests`: Notion API / Imgur 调用
- `python-telegram-bot`: Telegram推送
- `apscheduler`: 定时调度
- `pydantic-settings`: 配置管理

完整列表见 `requirements.txt`

## 许可证

MIT License
