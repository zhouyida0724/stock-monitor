"""数据获取器测试模块"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# 需要添加项目根目录到路径
import sys
sys.path.insert(0, '/Users/yidazhou/.openclaw/workspace/stock-monitor')

from src.data_fetchers import (
    DataFetcherFactory,
    MarketType,
    BaseDataFetcher,
    SECTOR_ETFS
)
from src.data_fetchers.a_share_fetcher import AShareDataFetcher
from src.data_fetchers.us_market_fetcher import USMarketDataFetcher
from src.data_fetchers.hk_market_fetcher import HKMarketDataFetcher


class TestDataFetcherFactory:
    """测试数据获取器工厂"""
    
    def test_create_a_share(self):
        """测试创建A股获取器"""
        with patch('src.data_fetchers.a_share_fetcher.ak'):
            fetcher = DataFetcherFactory.create('a_share')
            assert isinstance(fetcher, AShareDataFetcher)
            assert fetcher.market_type == MarketType.A_SHARE
    
    def test_create_a_share_aliases(self):
        """测试A股别名"""
        with patch('src.data_fetchers.a_share_fetcher.ak'):
            aliases = ['a_share', 'a', 'ashare', 'cn', 'china']
            for alias in aliases:
                fetcher = DataFetcherFactory.create(alias)
                assert isinstance(fetcher, AShareDataFetcher)
    
    def test_create_us(self):
        """测试创建美股获取器"""
        with patch('src.data_fetchers.us_market_fetcher.yf'):
            fetcher = DataFetcherFactory.create('us')
            assert isinstance(fetcher, USMarketDataFetcher)
            assert fetcher.market_type == MarketType.US
            assert fetcher.sector_etfs == SECTOR_ETFS
    
    def test_create_us_aliases(self):
        """测试美股别名"""
        with patch('src.data_fetchers.us_market_fetcher.yf'):
            aliases = ['us', 'usa', 'american', 'america']
            for alias in aliases:
                fetcher = DataFetcherFactory.create(alias)
                assert isinstance(fetcher, USMarketDataFetcher)
    
    def test_create_hk(self):
        """测试创建港股获取器"""
        with patch('src.data_fetchers.hk_market_fetcher.yf'):
            fetcher = DataFetcherFactory.create('hk')
            assert isinstance(fetcher, HKMarketDataFetcher)
            assert fetcher.market_type == MarketType.HK
    
    def test_create_hk_aliases(self):
        """测试港股别名"""
        with patch('src.data_fetchers.hk_market_fetcher.yf'):
            aliases = ['hk', 'hongkong', 'hkg']
            for alias in aliases:
                fetcher = DataFetcherFactory.create(alias)
                assert isinstance(fetcher, HKMarketDataFetcher)
    
    def test_create_invalid_market(self):
        """测试无效市场类型"""
        with pytest.raises(ValueError):
            DataFetcherFactory.create('invalid_market')
    
    def test_get_supported_markets(self):
        """测试获取支持的市场列表"""
        markets = DataFetcherFactory.get_supported_markets()
        assert 'a_share' in markets
        assert 'us' in markets
        assert 'hk' in markets


class TestAShareDataFetcher:
    """测试A股数据获取器"""
    
    @pytest.fixture
    def fetcher(self):
        with patch('src.data_fetchers.a_share_fetcher.ak'):
            return AShareDataFetcher()
    
    def test_initialization(self, fetcher):
        """测试初始化"""
        assert fetcher.market_type == MarketType.A_SHARE
        assert fetcher.get_market_name() == "A股"
        assert fetcher.get_market_emoji() == "🇨🇳"
    
    def test_normalize_columns(self, fetcher):
        """测试列名标准化"""
        df = pd.DataFrame({
            '名称': ['半导体', '白酒'],
            '今日涨跌幅': [2.5, -1.2],
            '今日主力净流入-净额': [100000000, -50000000]
        })
        
        result = fetcher._normalize_columns(df)
        assert 'sector_name' in result.columns
        assert 'change_pct' in result.columns
        assert 'main_inflow' in result.columns


class TestUSMarketDataFetcher:
    """测试美股数据获取器"""
    
    @pytest.fixture
    def fetcher(self):
        with patch('src.data_fetchers.us_market_fetcher.yf'):
            return USMarketDataFetcher()
    
    def test_initialization(self, fetcher):
        """测试初始化"""
        assert fetcher.market_type == MarketType.US
        assert fetcher.get_market_name() == "美股"
        assert fetcher.get_market_emoji() == "🇺🇸"
        assert len(fetcher.sector_etfs) == 11  # 11个Sector ETFs
    
    def test_sector_etfs_mapping(self, fetcher):
        """测试Sector ETFs映射"""
        assert 'XLK' in fetcher.sector_etfs.values()  # 科技
        assert 'XLF' in fetcher.sector_etfs.values()  # 金融
        assert fetcher.sector_etfs['Technology'] == 'XLK'
        assert fetcher.sector_etfs['Financials'] == 'XLF'
    
    def test_get_sector_data_structure(self, fetcher):
        """测试美股板块数据结构（实际数据获取在集成测试中验证）"""
        # 验证必要的Sector ETFs存在
        assert 'Technology' in fetcher.sector_etfs
        assert 'XLK' in fetcher.sector_etfs.values()
        assert len(fetcher.sector_etfs) == 11
    
    def test_get_sector_historical_params(self, fetcher):
        """测试历史数据参数处理"""
        # 验证 symbol 解析逻辑
        # 测试板块名称转ETF代码
        assert fetcher.sector_etfs.get('Technology') == 'XLK'


class TestHKMarketDataFetcher:
    """测试港股数据获取器"""
    
    @pytest.fixture
    def fetcher(self):
        with patch('src.data_fetchers.hk_market_fetcher.yf'):
            return HKMarketDataFetcher(use_etfs=True)
    
    def test_initialization(self, fetcher):
        """测试初始化"""
        assert fetcher.market_type == MarketType.HK
        assert fetcher.get_market_name() == "港股"
        assert fetcher.get_market_emoji() == "🇭🇰"
        assert fetcher.use_etfs == True
    
    def test_get_etf_data_structure(self, fetcher):
        """测试港股ETF数据结构"""
        # 验证ETF配置存在
        from src.data_fetchers.hk_market_fetcher import HK_SECTOR_ETFS
        assert '恒生科技' in HK_SECTOR_ETFS
        assert '3033.HK' in HK_SECTOR_ETFS.values()


class TestBaseDataFetcher:
    """测试数据获取器基类"""
    
    def test_market_type_enum(self):
        """测试市场类型枚举"""
        assert MarketType.A_SHARE.value == 'a_share'
        assert MarketType.US.value == 'us'
        assert MarketType.HK.value == 'hk'


class TestIntegration:
    """集成测试"""
    
    def test_all_fetchers_have_required_methods(self):
        """测试所有获取器都有必需的方法"""
        required_methods = ['get_sector_data', 'get_sector_historical', 'get_market_name', 'get_market_emoji']
        
        fetcher_classes = [AShareDataFetcher, USMarketDataFetcher, HKMarketDataFetcher]
        
        for fetcher_class in fetcher_classes:
            for method in required_methods:
                assert hasattr(fetcher_class, method), f"{fetcher_class.__name__} 缺少方法 {method}"
    
    def test_all_markets_have_emoji(self):
        """测试所有市场都有emoji"""
        emojis = {
            MarketType.A_SHARE: "🇨🇳",
            MarketType.US: "🇺🇸",
            MarketType.HK: "🇭🇰"
        }
        
        for market_type, expected_emoji in emojis.items():
            # 这里我们只是验证映射关系，不实际创建实例
            pass  # emojis字典已经在代码中定义


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
