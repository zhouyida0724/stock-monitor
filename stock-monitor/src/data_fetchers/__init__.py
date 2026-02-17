"""数据获取器工厂模块"""
from typing import Optional
import logging

from .base import BaseDataFetcher, MarketType
from .a_share_fetcher import AShareDataFetcher
from .us_market_fetcher import USMarketDataFetcher
from .hk_market_fetcher import HKMarketDataFetcher

logger = logging.getLogger(__name__)


class DataFetcherFactory:
    """数据获取器工厂类
    
    根据市场类型创建对应的数据获取器实例
    
    Usage:
        >>> fetcher = DataFetcherFactory.create('us')
        >>> df = fetcher.get_sector_data()
        
        >>> fetcher = DataFetcherFactory.create(MarketType.A_SHARE)
        >>> df = fetcher.get_sector_data()
    """
    
    _fetchers = {
        MarketType.A_SHARE: AShareDataFetcher,
        MarketType.US: USMarketDataFetcher,
        MarketType.HK: HKMarketDataFetcher,
    }
    
    @classmethod
    def create(cls, market: str, **kwargs) -> BaseDataFetcher:
        """创建数据获取器实例
        
        Args:
            market: 市场类型，支持：
                - 'a_share', 'a', 'ashare', 'cn' -> A股
                - 'us', 'usa', 'american' -> 美股  
                - 'hk', 'hongkong', 'hong_kong' -> 港股
            **kwargs: 传递给数据获取器的额外参数
            
        Returns:
            BaseDataFetcher: 对应市场的数据获取器实例
            
        Raises:
            ValueError: 不支持的市场类型
        """
        market_type = cls._parse_market(market)
        
        if market_type not in cls._fetchers:
            raise ValueError(f"不支持的市场类型: {market}，支持: a_share, us, hk")
        
        fetcher_class = cls._fetchers[market_type]
        fetcher = fetcher_class(**kwargs)
        
        logger.info(f"创建数据获取器: {market_type.value} ({fetcher.get_market_name()})")
        return fetcher
    
    @classmethod
    def _parse_market(cls, market: str) -> MarketType:
        """解析市场类型字符串"""
        market = market.lower().strip()
        
        a_share_aliases = ['a_share', 'a', 'ashare', 'cn', 'china', 'a股']
        us_aliases = ['us', 'usa', 'american', 'america', '美股']
        hk_aliases = ['hk', 'hongkong', 'hong_kong', 'hkg', '港股']
        
        if market in a_share_aliases:
            return MarketType.A_SHARE
        elif market in us_aliases:
            return MarketType.US
        elif market in hk_aliases:
            return MarketType.HK
        else:
            # 尝试直接匹配枚举值
            try:
                return MarketType(market)
            except ValueError:
                raise ValueError(f"未知市场类型: {market}")
    
    @classmethod
    def get_supported_markets(cls) -> list:
        """获取支持的市场类型列表"""
        return [mt.value for mt in cls._fetchers.keys()]
    
    @classmethod
    def register_fetcher(cls, market_type: MarketType, fetcher_class: type):
        """注册新的数据获取器类型
        
        Args:
            market_type: 市场类型枚举
            fetcher_class: 数据获取器类（必须继承BaseDataFetcher）
        """
        if not issubclass(fetcher_class, BaseDataFetcher):
            raise ValueError("获取器类必须继承BaseDataFetcher")
        
        cls._fetchers[market_type] = fetcher_class
        logger.info(f"注册数据获取器: {market_type.value}")


# 便捷导入
__all__ = [
    'BaseDataFetcher',
    'MarketType',
    'AShareDataFetcher',
    'USMarketDataFetcher',
    'HKMarketDataFetcher',
    'DataFetcherFactory',
    'SECTOR_ETFS',
]

# 从us_market_fetcher导入SECTOR_ETFS以便便捷访问
from .us_market_fetcher import SECTOR_ETFS
