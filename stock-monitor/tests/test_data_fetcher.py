"""DataFetcher模块测试"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from src.data_fetcher import DataFetcher


class TestDataFetcher:
    """DataFetcher数据获取器测试"""
    
    @pytest.fixture
    def fetcher(self):
        return DataFetcher()
    
    def test_get_sector_flow_success(self, fetcher, mock_akshare_data):
        """测试正常获取数据"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_rank', return_value=mock_akshare_data):
            df = fetcher.get_sector_flow()
            
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 5
            assert 'sector_name' in df.columns
            assert 'main_inflow' in df.columns
            assert df.iloc[0]['sector_name'] == '半导体'
    
    def test_get_sector_flow_with_trade_date(self, fetcher, mock_akshare_data):
        """测试指定交易日期的数据获取"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_rank', return_value=mock_akshare_data):
            df = fetcher.get_sector_flow(trade_date='20240215')
            
            assert isinstance(df, pd.DataFrame)
            assert 'trade_date' in df.columns
            assert df['trade_date'].iloc[0] == '20240215'
    
    def test_get_sector_flow_network_error(self, fetcher):
        """测试网络错误处理"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_rank', side_effect=Exception("Connection error")):
            with pytest.raises(ConnectionError):
                fetcher.get_sector_flow()
    
    def test_get_sector_flow_empty_data(self, fetcher):
        """测试空数据返回处理"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_rank', return_value=pd.DataFrame()):
            with pytest.raises(ValueError, match="API返回空数据"):
                fetcher.get_sector_flow()
    
    def test_get_sector_flow_none_data(self, fetcher):
        """测试None数据返回处理"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_rank', return_value=None):
            with pytest.raises(ValueError, match="API返回空数据"):
                fetcher.get_sector_flow()
    
    def test_normalize_columns_with_chinese_names(self, fetcher):
        """测试中文列名标准化"""
        df = pd.DataFrame({
            '名称': ['板块A', '板块B'],
            '今日涨跌幅': [1.5, 2.0],
            '今日主力净流入-净额': [1000000, 2000000],
            '今日主力净流入-净占比': [5.0, 10.0],
        })
        
        result = fetcher._normalize_columns(df)
        
        assert 'sector_name' in result.columns
        assert 'change_pct' in result.columns
        assert 'main_inflow' in result.columns
        assert 'main_inflow_pct' in result.columns
    
    def test_normalize_columns_without_prefix(self, fetcher):
        """测试不带"今日"前缀的列名标准化"""
        df = pd.DataFrame({
            '名称': ['板块A', '板块B'],
            '涨跌幅': [1.5, 2.0],
            '主力净流入-净额': [1000000, 2000000],
        })
        
        result = fetcher._normalize_columns(df)
        
        assert 'sector_name' in result.columns
        # 检查原始列仍然存在
        assert '涨跌幅' in result.columns
    
    def test_normalize_columns_partial_mapping(self, fetcher):
        """测试部分列名映射"""
        df = pd.DataFrame({
            '名称': ['板块A'],
            '今日超大单净流入-净额': [500000],
            '今日超大单净流入-净占比': [2.5],
        })
        
        result = fetcher._normalize_columns(df)
        
        assert 'sector_name' in result.columns
        assert 'super_large_inflow' in result.columns
        assert 'super_large_inflow_pct' in result.columns
    
    def test_normalize_columns_no_matching_columns(self, fetcher):
        """测试没有匹配列名的情况"""
        df = pd.DataFrame({
            'unknown_col1': [1, 2],
            'unknown_col2': ['a', 'b'],
        })

        result = fetcher._normalize_columns(df)

        # 列名应该保持不变
        assert 'unknown_col1' in result.columns
        assert 'unknown_col2' in result.columns


class TestDataFetcherHistorical:
    """历史数据获取功能测试"""

    @pytest.fixture
    def fetcher(self):
        return DataFetcher()

    @pytest.fixture
    def mock_historical_data(self):
        """提供模拟的历史数据"""
        return pd.DataFrame({
            '日期': ['2024-02-01', '2024-02-02', '2024-02-05', '2024-02-06', '2024-02-07'],
            '名称': ['半导体', '半导体', '半导体', '半导体', '半导体'],
            '主力净流入-净额': [100000000, 150000000, -50000000, 200000000, 80000000],
            '主力净流入-净占比': [2.5, 3.5, -1.2, 4.8, 2.1],
            '涨跌幅': [1.5, 2.3, -0.8, 3.2, 1.2],
        })

    def test_get_sector_flow_historical_success(self, fetcher, mock_historical_data):
        """测试正常获取板块历史数据"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=mock_historical_data):
            df = fetcher.get_sector_flow_historical('半导体', days=5)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 5
            assert 'date' in df.columns
            assert 'sector_name' in df.columns
            assert 'main_inflow' in df.columns
            assert 'change_pct' in df.columns
            assert df.iloc[0]['sector_name'] == '半导体'

    def test_get_sector_flow_historical_empty_response(self, fetcher):
        """测试空数据返回"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=pd.DataFrame()):
            df = fetcher.get_sector_flow_historical('半导体', days=5)

            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_get_sector_flow_historical_none_response(self, fetcher):
        """测试None返回"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=None):
            df = fetcher.get_sector_flow_historical('半导体', days=5)

            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_get_sector_flow_historical_api_error(self, fetcher):
        """测试API异常"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', side_effect=Exception("API Error")):
            df = fetcher.get_sector_flow_historical('半导体', days=5)

            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_get_sector_flow_historical_days_limit(self, fetcher, mock_historical_data):
        """测试天数限制"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=mock_historical_data):
            df = fetcher.get_sector_flow_historical('半导体', days=3)

            assert len(df) == 3  # 应该只返回最近3天

    def test_get_all_sectors_historical_success(self, fetcher, mock_historical_data):
        """测试批量获取多个板块历史数据"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=mock_historical_data):
            sectors = ['半导体', '电池', '光伏']
            df = fetcher.get_all_sectors_historical(sectors, days=5)

            assert isinstance(df, pd.DataFrame)
            # 3个板块，每个5条数据
            assert len(df) == 15
            assert 'sector_name' in df.columns

    def test_get_all_sectors_historical_partial_failure(self, fetcher, mock_historical_data):
        """测试部分板块获取失败的情况"""
        def side_effect(symbol):
            if symbol == '半导体':
                return mock_historical_data
            else:
                return pd.DataFrame()  # 其他板块返回空

        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', side_effect=side_effect):
            sectors = ['半导体', '电池', '光伏']
            df = fetcher.get_all_sectors_historical(sectors, days=5)

            assert isinstance(df, pd.DataFrame)
            # 只有半导体有数据
            assert len(df) == 5

    def test_get_all_sectors_historical_empty_sectors(self, fetcher):
        """测试空板块列表"""
        df = fetcher.get_all_sectors_historical([], days=5)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_backfill_historical_data_success(self, fetcher, mock_historical_data):
        """测试回填历史数据"""
        with patch('src.data_fetcher.ak.stock_sector_fund_flow_hist', return_value=mock_historical_data):
            sectors = ['半导体']
            df = fetcher.backfill_historical_data(sectors, end_date='2024-02-07', days=10)

            assert isinstance(df, pd.DataFrame)
            assert 'date' in df.columns
            # 数据应该被过滤到指定日期范围内

    def test_backfill_historical_data_invalid_date(self, fetcher):
        """测试无效日期格式"""
        df = fetcher.backfill_historical_data(['半导体'], end_date='invalid-date', days=10)

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_rate_limit_functionality(self, fetcher):
        """测试频率限制功能"""
        import time

        # 记录调用前的时间
        before_time = time.time()

        # 调用频率限制
        fetcher._rate_limit()

        # 如果没有上次请求时间，应该设置但不一定等待
        assert fetcher._last_request_time >= before_time

        # 第二次调用应该检查间隔
        fetcher._min_request_interval = 0.1  # 设置较短的间隔以便测试
        time.sleep(0.05)  # 稍微等待一下
        fetcher._rate_limit()
        assert fetcher._last_request_time >= before_time
