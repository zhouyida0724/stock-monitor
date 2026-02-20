"""测试Fixtures - 提供模拟数据和mock对象"""
import pytest
import pandas as pd
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

# 设置测试环境变量
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_for_unit_tests'
os.environ['TELEGRAM_CHAT_ID'] = '123456789'

# 添加src到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import Settings
from src.data_fetchers import BaseDataFetcher
from src.analyzer import SectorAnalyzer
from src.reporter import ReportGenerator
from src.notifier import TelegramNotifier
from src.scheduler import MonitorScheduler


@pytest.fixture
def mock_sector_data():
    """提供模拟的板块资金流数据"""
    return pd.DataFrame({
        'sector_name': ['半导体', '电池', '光伏', '电力', '有色', 
                        '银行', '证券', '保险', '白酒', '医药'],
        'main_inflow': [500000000, 400000000, 300000000, 250000000, 200000000,
                       -100000000, -150000000, -200000000, -250000000, -300000000],
        'main_inflow_pct': [5.0, 4.0, 3.0, 2.5, 2.0, 
                           -1.0, -1.5, -2.0, -2.5, -3.0],
        'super_large_inflow': [300000000, 200000000, 150000000, 100000000, 80000000,
                              -50000000, -80000000, -100000000, -120000000, -150000000],
        'change_pct': [3.5, 2.8, 2.1, 1.8, 1.5,
                      -0.5, -0.8, -1.0, -1.2, -1.5],
    })


@pytest.fixture
def mock_sector_data_raw():
    """提供原始格式（中文列名）的板块资金流数据"""
    return pd.DataFrame({
        '名称': ['半导体', '电池', '光伏', '电力', '有色', 
                '银行', '证券', '保险', '白酒', '医药'],
        '今日主力净流入-净额': [500000000, 400000000, 300000000, 250000000, 200000000,
                              -100000000, -150000000, -200000000, -250000000, -300000000],
        '今日主力净流入-净占比': [5.0, 4.0, 3.0, 2.5, 2.0, 
                                -1.0, -1.5, -2.0, -2.5, -3.0],
        '今日超大单净流入-净额': [300000000, 200000000, 150000000, 100000000, 80000000,
                               -50000000, -80000000, -100000000, -120000000, -150000000],
        '今日涨跌幅': [3.5, 2.8, 2.1, 1.8, 1.5,
                     -0.5, -0.8, -1.0, -1.2, -1.5],
    })


@pytest.fixture
def empty_dataframe():
    """提供空的DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def temp_data_dir(tmp_path):
    """提供临时数据目录"""
    return tmp_path / "test_data"


@pytest.fixture
def mock_settings():
    """提供模拟配置"""
    return Settings(
        TELEGRAM_BOT_TOKEN="test_token_12345",
        TELEGRAM_CHAT_ID="123456789"
    )


@pytest.fixture
def mock_telegram_bot():
    """提供模拟的Telegram Bot"""
    bot = MagicMock()
    bot.send_message = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def mock_akshare_data():
    """提供mock的akshare返回数据"""
    return pd.DataFrame({
        '名称': ['半导体', '电池', '光伏', '电力', '有色'],
        '今日主力净流入-净额': [500000000, 400000000, 300000000, 250000000, 200000000],
        '今日主力净流入-净占比': [5.0, 4.0, 3.0, 2.5, 2.0],
        '今日涨跌幅': [3.5, 2.8, 2.1, 1.8, 1.5],
    })


@pytest.fixture
def sample_rotation_signals():
    """提供模拟的轮动信号数据"""
    return [
        {'sector_name': '光伏', 'yesterday_rank': 15, 'signal_type': '新进入TOP10'},
        {'sector_name': '电力', 'yesterday_rank': 12, 'signal_type': '新进入TOP10'},
    ]


@pytest.fixture
def mock_scheduler_components():
    """提供模拟的调度器组件"""
    return {
        'data_fetcher': MagicMock(spec=BaseDataFetcher),
        'analyzer': MagicMock(spec=SectorAnalyzer),
        'reporter': MagicMock(spec=ReportGenerator),
        'notifier': MagicMock(spec=TelegramNotifier),
    }


@pytest.fixture
def mock_us_sector_data():
    """提供模拟的美股Sector ETF数据"""
    return pd.DataFrame({
        'sector_name': ['Technology', 'Financials', 'Health Care', 'Consumer Discretionary'],
        'symbol': ['XLK', 'XLF', 'XLV', 'XLY'],
        'change_pct': [2.5, 1.8, -0.5, 1.2],
        'main_inflow': [1500000, 1200000, -800000, 900000],
        'volume': [10000000, 8000000, 5000000, 6000000],
        'close_price': [180.5, 35.2, 125.8, 175.3],
    })


@pytest.fixture
def mock_hk_sector_data():
    """提供模拟的港股板块数据"""
    return pd.DataFrame({
        'sector_name': ['恒生科技', '恒生金融', '恒生地产'],
        'symbol': ['3033.HK', '2828.HK', '2801.HK'],
        'change_pct': [1.8, -0.5, 2.0],
        'main_inflow': [800000, -300000, 1200000],
        'volume': [5000000, 3000000, 4000000],
        'close_price': [5.25, 12.8, 8.9],
    })


@pytest.fixture
def multi_market_results():
    """提供多市场测试结果数据"""
    return {
        'a_share': {
            'success': True,
            'top10': pd.DataFrame({
                'sector_name': ['半导体', '电池'],
                'change_pct': [3.5, 2.8],
                'main_inflow': [500000000, 400000000],
            }),
            'rotation_signals': [{'sector_name': '光伏', 'yesterday_rank': 12}],
            'error': None,
        },
        'us': {
            'success': True,
            'top10': pd.DataFrame({
                'sector_name': ['Technology', 'Financials'],
                'symbol': ['XLK', 'XLF'],
                'change_pct': [2.5, 1.8],
                'main_inflow': [1500000, 1200000],
            }),
            'rotation_signals': [],
            'error': None,
        },
        'hk': {
            'success': True,
            'top10': pd.DataFrame({
                'sector_name': ['恒生科技', '恒生地产'],
                'symbol': ['3033.HK', '2801.HK'],
                'change_pct': [1.8, 2.0],
                'main_inflow': [800000, 1200000],
            }),
            'rotation_signals': [{'sector_name': '恒生地产', 'yesterday_rank': 15}],
            'error': None,
        },
    }
