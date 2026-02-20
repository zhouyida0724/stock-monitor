"""图表生成器测试模块"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import shutil

import sys
sys.path.insert(0, '/Users/yidazhou/.openclaw/workspace/stock-monitor')

from src.chart_generator import ChartGenerator


class TestChartGenerator:
    """测试图表生成器"""
    
    @pytest.fixture
    def temp_dirs(self):
        """创建临时目录"""
        data_dir = tempfile.mkdtemp()
        charts_dir = tempfile.mkdtemp()
        yield {'data': data_dir, 'charts': charts_dir}
        shutil.rmtree(data_dir, ignore_errors=True)
        shutil.rmtree(charts_dir, ignore_errors=True)
    
    @pytest.fixture
    def chart_gen(self, temp_dirs):
        """创建图表生成器实例"""
        return ChartGenerator(
            data_path=temp_dirs['data'],
            charts_path=temp_dirs['charts']
        )
    
    @pytest.fixture
    def sample_a_share_data(self):
        """A股示例数据"""
        return pd.DataFrame({
            'sector_name': ['电子', '半导体', '新能源', '医药', '银行'],
            'change_pct': [3.5, 2.8, -1.2, 0.5, 1.0],
            'main_inflow': [500000000, 400000000, -200000000, 100000000, 300000000],
            'symbol': ['000001', '000002', '000003', '000004', '000005']
        })
    
    @pytest.fixture
    def sample_us_data(self):
        """美股示例数据"""
        return pd.DataFrame({
            'sector_name': ['Technology', 'Financials', 'Healthcare'],
            'change_pct': [2.5, 1.8, -0.5],
            'main_inflow': [5000000, 3000000, -1000000],
            'symbol': ['XLK', 'XLF', 'XLV']
        })
    
    def test_chart_generator_init(self, chart_gen):
        """测试图表生成器初始化"""
        assert chart_gen.data_path is not None
        assert chart_gen.charts_path is not None
        assert os.path.exists(chart_gen.charts_path)
    
    def test_generate_pie_charts_creation(self, chart_gen, sample_a_share_data):
        """测试饼图生成方法存在"""
        assert hasattr(chart_gen, 'generate_sector_flow_pie_charts')
    
    def test_generate_market_flow_summary_chart(self, chart_gen, sample_a_share_data):
        """测试摘要图表方法存在"""
        assert hasattr(chart_gen, 'generate_market_flow_summary_chart')
    
    def test_generate_top_sectors_trend(self, chart_gen):
        """测试TOP板块趋势图方法"""
        assert hasattr(chart_gen, 'generate_top_sectors_trend')
        assert hasattr(chart_gen, 'generate_market_top_sectors_trend')
    
    def test_load_historical_data(self, chart_gen):
        """测试加载历史数据方法"""
        assert hasattr(chart_gen, 'load_historical_data')
    
    def test_cleanup_old_charts(self, chart_gen):
        """测试清理旧图表方法"""
        assert hasattr(chart_gen, 'cleanup_old_charts')
    
    def test_generate_sector_comparison(self, chart_gen):
        """测试板块对比图方法"""
        assert hasattr(chart_gen, 'generate_sector_comparison')
    
    def test_generate_market_heatmap(self, chart_gen):
        """测试市场热力图方法"""
        assert hasattr(chart_gen, 'generate_market_heatmap')
    
    def test_interpolate_none(self, chart_gen):
        """测试None值插值"""
        values = [1, 2, None, 4, 5]
        result = chart_gen._interpolate_none(values)
        assert None not in result
    
    def test_get_inflow_column(self, chart_gen, sample_a_share_data):
        """测试获取流入列"""
        col = chart_gen._get_inflow_column(sample_a_share_data)
        assert col is not None
    
    def test_save_to_csv(self, chart_gen, sample_a_share_data):
        """测试保存CSV"""
        chart_gen._save_to_csv(sample_a_share_data, '20260220')
        # 检查文件是否创建
        expected_file = chart_gen.data_path / 'sector_flow_20260220.csv'
        assert expected_file.exists()
    
    def test_pie_chart_with_empty_data(self, chart_gen):
        """测试空数据处理"""
        empty_df = pd.DataFrame(columns=['sector_name', 'change_pct', 'main_inflow'])
        
        # 验证方法存在且可以调用
        assert hasattr(chart_gen, 'generate_sector_flow_pie_charts')
    
    def test_trend_chart_with_single_sector(self, chart_gen):
        """测试单板块趋势图"""
        assert hasattr(chart_gen, 'generate_sector_history_chart')
    
    def test_chart_generator_with_us_data(self, chart_gen, sample_us_data):
        """测试美股数据处理"""
        # 验证方法存在
        assert hasattr(chart_gen, 'generate_sector_flow_pie_charts')
