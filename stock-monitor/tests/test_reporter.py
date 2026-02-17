"""报告生成模块单元测试 - 多市场支持"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock

from src.reporter import ReportGenerator


class TestReportGeneratorMultiMarket:
    """测试报告生成器的多市场功能"""
    
    @pytest.fixture
    def reporter(self):
        return ReportGenerator()
    
    def test_generate_multi_markdown(self, reporter, multi_market_results):
        """测试生成多市场综合报告"""
        report = reporter.generate_multi_markdown(multi_market_results)
        
        # 验证报告包含所有市场
        assert "# 📊 多市场板块监控" in report
        assert "🇨🇳 A股板块资金流向" in report
        assert "🇺🇸 美股板块表现" in report
        assert "🇭🇰 港股行业指数" in report
        
        # 验证包含TOP10排名
        assert "### 🔥 TOP10 排名" in report
        assert "半导体" in report
        assert "Technology" in report
        assert "恒生科技" in report
        
        # 验证包含轮动信号
        assert "### 🔄 轮动信号" in report
        assert "光伏" in report
        assert "恒生地产" in report
    
    def test_generate_multi_markdown_partial_failure(self, reporter):
        """测试部分市场失败的报告生成"""
        results = {
            'a_share': {
                'success': True,
                'top10': pd.DataFrame({
                    'sector_name': ['半导体'],
                    'change_pct': [3.5],
                    'main_inflow': [500000000],
                }),
                'rotation_signals': [],
            },
            'us': {
                'success': False,
                'error': 'API限制',
            },
        }
        
        report = reporter.generate_multi_markdown(results)
        
        # 验证成功市场的数据存在
        assert "半导体" in report
        
        # 验证失败市场的错误信息存在
        assert "API限制" in report
        assert "获取失败" in report
    
    def test_generate_multi_markdown_empty_rotation(self, reporter):
        """测试无轮动信号的报告"""
        results = {
            'a_share': {
                'success': True,
                'top10': pd.DataFrame({
                    'sector_name': ['半导体'],
                    'change_pct': [3.5],
                    'main_inflow': [500000000],
                }),
                'rotation_signals': [],
            },
        }
        
        report = reporter.generate_multi_markdown(results)
        
        assert "今日无新进入TOP10的板块" in report
    
    def test_generate_market_section(self, reporter):
        """测试生成单个市场章节"""
        result = {
            'success': True,
            'top10': pd.DataFrame({
                'sector_name': ['Sector1', 'Sector2'],
                'symbol': ['S1', 'S2'],
                'change_pct': [2.0, 1.5],
                'main_inflow': [1000000, 800000],
            }),
            'rotation_signals': [
                {'sector_name': 'Sector1', 'yesterday_rank': 15}
            ],
        }
        
        lines = reporter._generate_market_section(result, "测试市场", "Test")
        
        assert "## 测试市场" in lines
        assert "Sector1" in '\n'.join(lines)
        assert "Sector2" in '\n'.join(lines)
        assert "昨日排名：#15" in '\n'.join(lines)
    
    def test_get_inflow_value(self, reporter):
        """测试提取净流入值"""
        # A股数据（单位是分）
        a_share_row = {'main_inflow': 500000000}  # 5亿分 = 5亿元
        assert reporter._get_inflow_value(a_share_row) == 5.0
        
        # 美股数据（较小值）
        us_row = {'main_inflow': 1500000}  # 被当作每股价格*股数，转换后较小
        result = reporter._get_inflow_value(us_row)
        assert result < 1.0
        
        # 带symbol字段的美股数据
        us_row_with_symbol = {
            'main_inflow': 1500000,
            'symbol': 'XLK'
        }
        result = reporter._get_inflow_value(us_row_with_symbol)
        assert result is not None
    
    def test_generate_market_summary(self, reporter, multi_market_results):
        """测试生成多市场摘要"""
        summary = reporter.generate_market_summary(multi_market_results)
        
        assert "A股:" in summary
        assert "美股:" in summary
        assert "港股:" in summary
        assert "半导体" in summary
        assert "Technology" in summary
        assert "恒生科技" in summary
    
    def test_generate_market_summary_no_data(self, reporter):
        """测试无数据时的摘要"""
        results = {
            'a_share': {'success': False, 'error': 'API错误'},
            'us': {'success': False, 'error': '网络错误'},
        }
        
        summary = reporter.generate_market_summary(results)
        assert summary == "无数据"


class TestReportGeneratorBackwardCompatibility:
    """测试报告生成器的向后兼容性"""
    
    @pytest.fixture
    def reporter(self):
        return ReportGenerator()
    
    def test_generate_markdown(self, reporter, mock_sector_data, sample_rotation_signals):
        """测试旧的单市场报告生成"""
        report = reporter.generate_markdown(mock_sector_data, sample_rotation_signals)
        
        assert "板块资金流向监控" in report
        assert "TOP10 板块" in report
        assert "半导体" in report
        assert "轮动信号" in report
        assert "光伏" in report
        assert "昨日排名：#15" in report
    
    def test_generate_markdown_empty_data(self, reporter):
        """测试空数据报告"""
        report = reporter.generate_markdown(pd.DataFrame(), [])
        
        assert "暂无数据" in report
        assert "今日无新进入TOP10的板块" in report
    
    def test_generate_summary(self, reporter, mock_sector_data):
        """测试生成简短摘要"""
        summary = reporter.generate_summary(mock_sector_data)
        
        assert "TOP3:" in summary
        assert "半导体" in summary
        assert "电池" in summary
        assert "光伏" in summary
    
    def test_generate_summary_empty(self, reporter):
        """测试空数据摘要"""
        summary = reporter.generate_summary(pd.DataFrame())
        assert summary == "无数据"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
