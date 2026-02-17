# 多市场扩展设计方案

## 概述

将现有的 A 股板块资金流监控扩展到美股和港股市场。

## 核心挑战

| 市场 | 主要差异 | 解决方案 |
|------|----------|----------|
| A股 | 板块资金流数据完整 | 保持现有实现 |
| 美股 | 无直接板块资金流数据 | 使用 Sector ETF 涨跌幅+资金流向作为替代指标 |
| 港股 | 板块资金流数据有限 | 使用行业指数+ETF组合 |

## 数据源选择

### 美股数据源
- **主要**: Yahoo Finance (yfinance) - 免费、稳定
- **备选**: Finnhub API (需 API Key) - 更专业的资金流向数据
- **板块代表**: 使用 Sector SPDR ETFs (XLK, XLF, XLK, XLE 等)

### 港股数据源
- **主要**: AKShare 港股接口 (免费)
- **备选**: Yahoo Finance
- **板块代表**: 恒生行业指数 + 港股 ETF

## 架构设计

### 1. 抽象数据获取层

```python
# src/data_fetchers/base.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Optional
from enum import Enum

class MarketType(Enum):
    A_SHARE = "a_share"
    US = "us"
    HK = "hk"

class BaseDataFetcher(ABC):
    """数据获取器基类"""
    
    def __init__(self, market: MarketType):
        self.market = market
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取板块数据
        返回统一格式:
        - sector_name: 板块名称
        - sector_code: 板块代码 (ETF代码/指数代码)
        - change_pct: 涨跌幅%
        - main_inflow: 主力净流入 (如可用)
        - volume: 成交量
        - market: 市场类型
        """
        pass
    
    @abstractmethod
    def get_sector_historical(self, sector_code: str, days: int = 30) -> pd.DataFrame:
        """获取板块历史数据"""
        pass
    
    @property
    @abstractmethod
    def currency(self) -> str:
        """返回货币单位 (CNY/USD/HKD)"""
        pass
```

### 2. 具体实现

#### A股 (现有)
```python
# src/data_fetchers/a_share_fetcher.py
class AShareDataFetcher(BaseDataFetcher):
    def __init__(self):
        super().__init__(MarketType.A_SHARE)
        self._fetcher = DataFetcher()  # 复用现有实现
    
    @property
    def currency(self) -> str:
        return "CNY"
```

#### 美股
```python
# src/data_fetchers/us_market_fetcher.py
import yfinance as yf

class USMarketDataFetcher(BaseDataFetcher):
    """美股板块数据获取器"""
    
    # Sector SPDR ETFs 映射
    SECTOR_ETFS = {
        "Technology": "XLK",           # 科技
        "Financials": "XLF",           # 金融
        "Health Care": "XLV",          # 医疗保健
        "Consumer Discretionary": "XLY",  # 可选消费
        "Communication Services": "XLC",  # 通信服务
        "Industrials": "XLI",          # 工业
        "Consumer Staples": "XLP",     # 必需消费
        "Energy": "XLE",               # 能源
        "Utilities": "XLU",            # 公用事业
        "Real Estate": "XLRE",         # 房地产
        "Materials": "XLB",            # 材料
    }
    
    def __init__(self):
        super().__init__(MarketType.US)
    
    @property
    def currency(self) -> str:
        return "USD"
    
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取美股板块ETF数据"""
        data = []
        
        for sector, ticker in self.SECTOR_ETFS.items():
            try:
                etf = yf.Ticker(ticker)
                info = etf.info
                hist = etf.history(period="2d")
                
                if len(hist) >= 2:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
                    volume = latest['Volume']
                    
                    # 估算资金流入 (简化版：价格变化 × 成交量)
                    estimated_inflow = (latest['Close'] - prev['Close']) * volume
                    
                    data.append({
                        'sector_name': sector,
                        'sector_code': ticker,
                        'change_pct': change_pct,
                        'main_inflow': estimated_inflow,
                        'volume': volume,
                        'market': self.market.value,
                        'close_price': latest['Close']
                    })
            except Exception as e:
                self.logger.warning(f"获取 {ticker} 数据失败: {e}")
                continue
        
        return pd.DataFrame(data)
    
    def get_sector_historical(self, sector_code: str, days: int = 30) -> pd.DataFrame:
        """获取ETF历史数据"""
        try:
            etf = yf.Ticker(sector_code)
            hist = etf.history(period=f"{days}d")
            
            if hist.empty:
                return pd.DataFrame()
            
            # 获取板块名称
            sector_name = None
            for s, code in self.SECTOR_ETFS.items():
                if code == sector_code:
                    sector_name = s
                    break
            
            hist = hist.reset_index()
            hist['date'] = hist['Date'].dt.strftime('%Y-%m-%d')
            hist['sector_code'] = sector_code
            hist['sector_name'] = sector_name
            hist['market'] = self.market.value
            
            # 计算涨跌幅
            hist['change_pct'] = hist['Close'].pct_change() * 100
            
            # 估算资金流入
            hist['main_inflow'] = (hist['Close'].diff()) * hist['Volume']
            
            return hist[['date', 'sector_name', 'sector_code', 'change_pct', 
                        'main_inflow', 'volume', 'close_price', 'market']]
            
        except Exception as e:
            self.logger.error(f"获取 {sector_code} 历史数据失败: {e}")
            return pd.DataFrame()
```

#### 港股
```python
# src/data_fetchers/hk_market_fetcher.py
import akshare as ak

class HKMarketDataFetcher(BaseDataFetcher):
    """港股板块数据获取器"""
    
    # 恒生行业指数代码映射
    SECTOR_INDICES = {
        "能源": "HSCEI",           # 恒生能源
        "原材料": "HSCIC",         # 恒生原材料
        "工业": "HSCII",           # 恒生工业
        "消费品": "HSCGD",         # 恒生消费品制造
        "服务": "HSCGS",           # 恒生服务业
        "电讯": "HSCT",           # 恒生电讯
        "公用": "HSCU",           # 恒生公用事业
        "金融": "HSCI",            # 恒生金融
        "地产": "HSP",             # 恒生地产
        "信息科技": "HSIT",        # 恒生资讯科技
    }
    
    def __init__(self):
        super().__init__(MarketType.HK)
    
    @property
    def currency(self) -> str:
        return "HKD"
    
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取港股行业指数数据"""
        # 使用 AKShare 获取恒生行业指数
        # 或使用 Yahoo Finance 获取港股ETF
        pass
```

### 3. 数据获取工厂

```python
# src/data_fetchers/__init__.py
from .base import MarketType, BaseDataFetcher
from .a_share_fetcher import AShareDataFetcher
from .us_market_fetcher import USMarketDataFetcher
from .hk_market_fetcher import HKMarketDataFetcher

class DataFetcherFactory:
    """数据获取器工厂"""
    
    _fetchers = {
        MarketType.A_SHARE: AShareDataFetcher,
        MarketType.US: USMarketDataFetcher,
        MarketType.HK: HKMarketDataFetcher,
    }
    
    @classmethod
    def create(cls, market: MarketType) -> BaseDataFetcher:
        """创建对应市场的数据获取器"""
        if market not in cls._fetchers:
            raise ValueError(f"不支持的市场类型: {market}")
        return cls._fetchers[market]()
    
    @classmethod
    def create_all(cls, markets: List[MarketType]) -> List[BaseDataFetcher]:
        """创建多个市场的数据获取器"""
        return [cls.create(m) for m in markets]
```

## 配置扩展

### .env 新增配置

```bash
# 市场配置
ENABLED_MARKETS=a_share,us,hk

# A股配置 (现有)
A_SHARE_SCHEDULE_TIME=15:05

# 美股配置 (北京时间第二天早上显示前一日收盘)
US_SCHEDULE_TIME=07:00
US_TIMEZONE=America/New_York

# 港股配置
HK_SCHEDULE_TIME=16:05
HK_TIMEZONE=Asia/Hong_Kong

# Yahoo Finance (美股/港股使用)
# 无需API Key，但可选配置代理
YF_PROXY=http://proxy.example.com:8080

# Finnhub API (美股更精确的资金流，可选)
FINNHUB_API_KEY=your_finnhub_key
```

### Settings 类更新

```python
# src/config.py
from typing import List
from enum import Enum

class MarketType(str, Enum):
    A_SHARE = "a_share"
    US = "us"
    HK = "hk"

class MarketConfig(BaseModel):
    """单个市场配置"""
    market: MarketType
    schedule_time: str
    timezone: str
    enabled: bool = True

class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 多市场配置
    ENABLED_MARKETS: str = "a_share"  # 逗号分隔: a_share,us,hk
    
    # 各市场调度时间 (考虑时区)
    A_SHARE_SCHEDULE_TIME: str = "15:05"
    US_SCHEDULE_TIME: str = "07:00"      # 北京时间显示美股前日收盘
    HK_SCHEDULE_TIME: str = "16:05"
    
    # 时区配置
    US_TIMEZONE: str = "America/New_York"
    HK_TIMEZONE: str = "Asia/Hong_Kong"
    
    @property
    def enabled_markets(self) -> List[MarketType]:
        """解析启用的市场列表"""
        markets = []
        for m in self.ENABLED_MARKETS.split(','):
            m = m.strip()
            if m:
                markets.append(MarketType(m))
        return markets
```

## Notion 数据结构

### 页面标题格式
```
📊 板块监控 - 2026-02-17
├── A股板块资金流向
├── 美股板块表现 (Sector ETFs)
└── 港股行业指数
```

### 统一报告格式

```markdown
# 📊 多市场板块监控 - 2026-02-17

## 🇨🇳 A股板块资金流向

| 排名 | 板块 | 净流入(亿) | 涨跌幅 |
|------|------|------------|--------|
| 1 | 半导体 | +12.5 | +2.3% |

## 🇺🇸 美股板块表现 (Sector ETFs)

| 排名 | 板块 | ETF | 涨跌 | 资金流向估算 |
|------|------|-----|------|--------------|
| 1 | 科技 | XLK | +1.2% | +$2.1B |

## 🇭🇰 港股行业指数

| 排名 | 行业 | 指数 | 涨跌幅 |
|------|------|------|--------|
| 1 | 科技 | HSIT | +1.8% |
```

## 调度策略

### 多市场调度器

```python
# src/multi_market_scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

class MultiMarketScheduler:
    """多市场监控调度器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(__name__)
    
    def _create_market_job(self, market: MarketType):
        """为单个市场创建定时任务"""
        
        # 获取市场配置
        if market == MarketType.A_SHARE:
            schedule_time = self.settings.A_SHARE_SCHEDULE_TIME
            timezone = "Asia/Shanghai"
            days = "mon-fri"  # A股工作日
        elif market == MarketType.US:
            schedule_time = self.settings.US_SCHEDULE_TIME
            timezone = self.settings.US_TIMEZONE
            days = "tue-sat"  # 美股周一到周五，北京时间周二到周六早上
        elif market == MarketType.HK:
            schedule_time = self.settings.HK_SCHEDULE_TIME
            timezone = self.settings.HK_TIMEZONE
            days = "mon-fri"
        
        hour, minute = map(int, schedule_time.split(':'))
        
        # 创建触发器
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=days,
            timezone=pytz.timezone(timezone)
        )
        
        # 添加任务
        self.scheduler.add_job(
            self._run_market_monitor,
            trigger=trigger,
            args=[market],
            id=f'monitor_{market.value}',
            name=f'{market.value} Market Monitor',
            replace_existing=True
        )
        
        self.logger.info(f"已调度 {market.value} 市场，时间: {schedule_time} ({timezone})")
```

## 文件结构

```
stock-monitor/
├── src/
│   ├── __init__.py
│   ├── config.py                    # 配置管理 (更新)
│   ├── data_fetchers/               # 新增目录
│   │   ├── __init__.py              # 工厂类
│   │   ├── base.py                  # 抽象基类
│   │   ├── a_share_fetcher.py       # A股实现
│   │   ├── us_market_fetcher.py     # 美股实现
│   │   └── hk_market_fetcher.py     # 港股实现
│   ├── analyzer.py                  # 复用 (增加 market 字段处理)
│   ├── chart_generator.py           # 复用
│   ├── reporter.py                  # 更新 (支持多市场报告)
│   ├── notion_writer.py             # 复用
│   └── multi_market_scheduler.py    # 新增
├── main.py                          # 更新 (支持多市场)
├── generate_historical_report.py    # 更新 (支持多市场)
└── requirements.txt                 # 新增 yfinance
```

## 实施步骤

### Phase 1: 基础设施 (1-2天)
1. 创建 `src/data_fetchers/` 目录结构
2. 实现 `BaseDataFetcher` 抽象基类
3. 重构现有 `DataFetcher` 为 `AShareDataFetcher`
4. 实现 `DataFetcherFactory`

### Phase 2: 美股实现 (2-3天)
1. 实现 `USMarketDataFetcher`
2. 集成 yfinance
3. 测试 Sector ETF 数据获取
4. 验证历史数据回填

### Phase 3: 港股实现 (1-2天)
1. 实现 `HKMarketDataFetcher`
2. 调研 AKShare 港股接口
3. 测试恒生指数数据

### Phase 4: 调度与报告 (1-2天)
1. 实现 `MultiMarketScheduler`
2. 更新报告生成器支持多市场
3. 更新配置管理
4. 更新主入口

### Phase 5: 测试与优化 (2-3天)
1. 多市场并行测试
2. 错误处理优化
3. 文档更新

## 依赖新增

```txt
# requirements.txt 新增
yfinance>=0.2.28
pytz>=2023.3
```

## 风险与注意事项

1. **数据源稳定性**: Yahoo Finance 偶尔会有访问限制，需要添加重试机制
2. **数据准确性**: 美股使用的是ETF作为板块代理，与真实板块资金流有差异，需要在报告中注明
3. **时区处理**: 美股在北京时间早上显示前一日数据，需要清晰的日期标注
4. **API限制**: 如需使用 Finnhub 等付费API，需要考虑调用频率限制

## 成本估算

| 项目 | 成本 | 说明 |
|------|------|------|
| Yahoo Finance | 免费 | 有频率限制 |
| Finnhub (可选) | 免费额度/月 $0-50 | 更精确的资金流数据 |
| AKShare 港股 | 免费 | 现有依赖 |
| Notion | 免费/现有 | 无额外成本 |

---

**总结**: 通过抽象数据获取层，可以在保持现有A股功能不变的情况下，平滑扩展到美股和港股市场。美股使用 Sector ETF 作为板块代理指标，虽然与A股的资金流向数据类型不同，但可以作为有效的市场热度参考。
