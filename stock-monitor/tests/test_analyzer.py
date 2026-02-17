"""SectorAnalyzer模块测试"""
import pytest
import pandas as pd
import os
from datetime import datetime
from src.analyzer import SectorAnalyzer


class TestSectorAnalyzer:
    """SectorAnalyzer板块分析器测试"""
    
    @pytest.fixture
    def analyzer(self, temp_data_dir):
        return SectorAnalyzer(data_path=str(temp_data_dir))
    
    def test_rank_by_inflow_normal(self, analyzer, mock_sector_data):
        """测试正常排序"""
        result = analyzer.rank_by_inflow(mock_sector_data, top_n=10)
        
        assert len(result) == 10
        assert 'rank' in result.columns
        # 第一名的净流入应该最高
        assert result.iloc[0]['main_inflow'] == 500000000
        assert result.iloc[0]['rank'] == 1
        # 最后一名净流入最低
        assert result.iloc[-1]['main_inflow'] == -300000000
    
    def test_rank_by_inflow_top_n(self, analyzer, mock_sector_data):
        """测试TOP N限制"""
        result = analyzer.rank_by_inflow(mock_sector_data, top_n=3)
        
        assert len(result) == 3
        assert result.iloc[0]['sector_name'] == '半导体'
        assert result.iloc[1]['sector_name'] == '电池'
        assert result.iloc[2]['sector_name'] == '光伏'
    
    def test_rank_by_inflow_empty_data(self, analyzer, empty_dataframe):
        """测试空数据排序"""
        result = analyzer.rank_by_inflow(empty_dataframe)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_rank_by_inflow_none_input(self, analyzer):
        """测试None输入"""
        result = analyzer.rank_by_inflow(None)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_rank_by_inflow_fallback_column(self, analyzer):
        """测试备用列名排序"""
        # 没有main_inflow列，但有其他净流入列
        df = pd.DataFrame({
            'name': ['A', 'B', 'C'],
            '净流入金额': [100, 200, 50],
        })
        
        result = analyzer.rank_by_inflow(df)
        
        assert len(result) == 3
        assert result.iloc[0]['净流入金额'] == 200
    
    def test_detect_rotation_normal(self, analyzer):
        """测试正常轮动检测"""
        today_df = pd.DataFrame({
            'sector_name': ['A', 'B', 'C', 'D'],
            'main_inflow': [100, 90, 80, 70],
        })
        
        yesterday_df = pd.DataFrame({
            'sector_name': ['B', 'C', 'E', 'F'],
            'main_inflow': [100, 90, 80, 70],
            'rank': [1, 2, 3, 4],
        })
        
        signals = analyzer.detect_rotation(today_df, yesterday_df)
        
        # A和D是新进入TOP4的
        assert len(signals) == 2
        sector_names = [s['sector_name'] for s in signals]
        assert 'A' in sector_names
        assert 'D' in sector_names
    
    def test_detect_rotation_empty_today(self, analyzer, mock_sector_data, empty_dataframe):
        """测试今日数据为空"""
        signals = analyzer.detect_rotation(empty_dataframe, mock_sector_data)
        
        assert len(signals) == 0
    
    def test_detect_rotation_empty_yesterday(self, analyzer, mock_sector_data):
        """测试昨日数据为空"""
        signals = analyzer.detect_rotation(mock_sector_data, pd.DataFrame())
        
        assert len(signals) == 0
    
    def test_detect_rotation_none_inputs(self, analyzer):
        """测试None输入"""
        signals = analyzer.detect_rotation(None, None)
        
        assert len(signals) == 0
    
    def test_detect_rotation_use_name_column(self, analyzer):
        """测试使用'name'列而非'sector_name'"""
        today_df = pd.DataFrame({
            'name': ['A', 'B', 'C'],
            'main_inflow': [100, 90, 80],
        })
        
        yesterday_df = pd.DataFrame({
            'name': ['B', 'C', 'D'],
            'main_inflow': [100, 90, 80],
        })
        
        signals = analyzer.detect_rotation(today_df, yesterday_df)
        
        assert len(signals) == 1
        assert signals[0]['sector_name'] == 'A'
    
    def test_save_snapshot_success(self, analyzer, mock_sector_data):
        """测试数据保存成功"""
        file_path = analyzer.save_snapshot(mock_sector_data, '2024-02-15')
        
        assert os.path.exists(file_path)
        assert 'sector_flow_20240215.csv' in file_path
        
        # 验证文件内容
        loaded_df = pd.read_csv(file_path)
        assert len(loaded_df) == 10
    
    def test_save_snapshot_dash_date(self, analyzer, mock_sector_data):
        """测试带横线的日期格式"""
        file_path = analyzer.save_snapshot(mock_sector_data, '2024-02-15')
        
        assert os.path.exists(file_path)
        assert 'sector_flow_20240215.csv' in file_path
    
    def test_save_snapshot_no_dash_date(self, analyzer, mock_sector_data):
        """测试不带横线的日期格式"""
        file_path = analyzer.save_snapshot(mock_sector_data, '20240215')
        
        assert os.path.exists(file_path)
        assert 'sector_flow_20240215.csv' in file_path
    
    def test_load_snapshot_success(self, analyzer, mock_sector_data):
        """测试数据加载成功"""
        # 先保存
        analyzer.save_snapshot(mock_sector_data, '2024-02-15')
        
        # 再加载
        loaded_df = analyzer.load_snapshot('2024-02-15')
        
        assert loaded_df is not None
        assert len(loaded_df) == 10
        assert 'sector_name' in loaded_df.columns
    
    def test_load_snapshot_not_exists(self, analyzer):
        """测试加载不存在的文件"""
        result = analyzer.load_snapshot('2020-01-01')
        
        assert result is None
    
    def test_load_snapshot_invalid_file(self, analyzer, temp_data_dir):
        """测试加载无效文件"""
        # 创建一个不符合期望格式的CSV文件
        invalid_file = temp_data_dir / "sector_flow_20240215.csv"
        invalid_file.write_text("not,a,valid,csv\ninvalid,data")
        
        # pandas能读取这个文件，只是列名不对
        result = analyzer.load_snapshot('2024-02-15')
        
        # pandas会尝试解析，返回一个DataFrame，但列名不是我们期望的
        # 根据实现，只要不是异常就会返回DataFrame
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # 有一行数据
    
    def test_get_last_trading_date_weekday(self, analyzer):
        """测试工作日获取上一个交易日"""
        # 周三 (2024-02-14)
        result = analyzer.get_last_trading_date('2024-02-14')
        
        assert result == '2024-02-13'
    
    def test_get_last_trading_date_monday(self, analyzer):
        """测试周一获取上一个交易日（应跳过周末）"""
        # 周一 (2024-02-12)
        result = analyzer.get_last_trading_date('2024-02-12')
        
        assert result == '2024-02-09'
    
    def test_get_last_trading_date_sunday(self, analyzer):
        """测试周日（非正常交易日，但测试逻辑）"""
        # 周日 (2024-02-11)
        result = analyzer.get_last_trading_date('2024-02-11')
        
        assert result == '2024-02-09'
    
    def test_duplicate_data_handling(self, analyzer):
        """测试重复数据处理"""
        df_with_duplicates = pd.DataFrame({
            'sector_name': ['A', 'A', 'B', 'B'],
            'main_inflow': [100, 100, 200, 200],
        })
        
        result = analyzer.rank_by_inflow(df_with_duplicates)
        
        # 即使有重复数据也应该能处理
        assert len(result) == 4
