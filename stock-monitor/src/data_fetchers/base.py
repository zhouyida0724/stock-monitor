"""数据获取器基类模块"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
import pandas as pd
import logging


class MarketType(Enum):
    """市场类型枚举"""
    A_SHARE = "a_share"      # A股
    US = "us"                # 美股
    HK = "hk"                # 港股


class BaseDataFetcher(ABC):
    """数据获取器抽象基类
    
    支持多市场的板块数据获取，包括：
    - A股：通过AKShare获取板块资金流
    - 美股：通过yfinance获取Sector ETFs数据
    - 港股：通过AKShare或yfinance获取行业指数
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.market_type: MarketType = None  # 子类必须设置
    
    @abstractmethod
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取当日板块数据
        
        Args:
            trade_date: 交易日期，格式 YYYYMMDD，None表示获取最新数据
            
        Returns:
            pd.DataFrame: 板块数据，必须包含以下列：
                - sector_name: 板块名称
                - change_pct: 涨跌幅 (%)
                - main_inflow: 主力净流入（或估算值）
                - volume: 成交量（可选）
                
        Raises:
            ConnectionError: 网络错误
            ValueError: API返回空数据
        """
        pass
    
    @abstractmethod
    def get_sector_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取单个板块/ETF的历史数据
        
        Args:
            symbol: 板块标识（A股为板块名称，美股/港股为ETF代码）
            days: 获取最近多少天的数据
            
        Returns:
            pd.DataFrame: 历史数据，包含以下列：
                - date: 日期 (YYYY-MM-DD)
                - sector_name: 板块名称
                - main_inflow: 净流入（或估算值）
                - change_pct: 涨跌幅
                - close_price: 收盘价（可选）
                - volume: 成交量（可选）
        """
        pass
    
    def get_market_name(self) -> str:
        """获取市场名称（用于显示）"""
        market_names = {
            MarketType.A_SHARE: "A股",
            MarketType.US: "美股", 
            MarketType.HK: "港股"
        }
        return market_names.get(self.market_type, "未知市场")
    
    def get_market_emoji(self) -> str:
        """获取市场对应的emoji"""
        emojis = {
            MarketType.A_SHARE: "🇨🇳",
            MarketType.US: "🇺🇸",
            MarketType.HK: "🇭🇰"
        }
        return emojis.get(self.market_type, "📊")
