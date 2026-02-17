"""多市场调度器单元测试"""
import pytest
import asyncio
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from src.multi_market_scheduler import MultiMarketScheduler, MarketSchedule
from src.analyzer import SectorAnalyzer
from src.reporter import ReportGenerator


class TestMarketSchedule:
    """测试市场调度配置"""
    
    def test_market_schedule_creation(self):
        """测试创建调度配置"""
        schedule = MarketSchedule(
            market='us',
            enabled=True,
            schedule_time='06:00',
            days_of_week='tue-sat'
        )
        assert schedule.market == 'us'
        assert schedule.enabled is True
        assert schedule.schedule_time == '06:00'
        assert schedule.days_of_week == 'tue-sat'


class TestMultiMarketScheduler:
    """测试多市场调度器"""
    
    @pytest.fixture
    def mock_components(self):
        """创建模拟组件"""
        analyzer = Mock(spec=SectorAnalyzer)
        analyzer.data_path = './test_data'
        
        reporter = Mock(spec=ReportGenerator)
        notifier = Mock()
        notion_writer = Mock()
        
        return {
            'analyzer': analyzer,
            'reporter': reporter,
            'notifier': notifier,
            'notion_writer': notion_writer,
        }
    
    @pytest.fixture
    def scheduler(self, mock_components):
        """创建调度器实例"""
        return MultiMarketScheduler(
            analyzer=mock_components['analyzer'],
            reporter=mock_components['reporter'],
            notifier=mock_components['notifier'],
            notion_writer=mock_components['notion_writer'],
            output_mode='notion'
        )
    
    def test_default_schedules(self):
        """测试默认调度配置"""
        schedules = MultiMarketScheduler.DEFAULT_SCHEDULES
        
        assert 'a_share' in schedules
        assert schedules['a_share'].schedule_time == '15:05'
        assert schedules['a_share'].days_of_week == 'mon-fri'
        
        assert 'us' in schedules
        assert schedules['us'].schedule_time == '06:00'
        assert schedules['us'].days_of_week == 'tue-sat'
        
        assert 'hk' in schedules
        assert schedules['hk'].schedule_time == '16:05'
        assert schedules['hk'].days_of_week == 'mon-fri'
    
    @pytest.mark.asyncio
    async def test_run_single_market_success(self, scheduler, mock_components):
        """测试运行单个市场成功"""
        # 模拟数据
        mock_df = pd.DataFrame({
            'sector_name': ['Tech', 'Finance'],
            'change_pct': [2.0, 1.5],
            'main_inflow': [1000000, 800000],
        })
        
        # 配置mock
        mock_components['analyzer'].rank_by_inflow.return_value = mock_df
        mock_components['analyzer'].get_last_trading_date.return_value = '2024-01-01'
        mock_components['analyzer'].detect_rotation.return_value = []
        mock_components['reporter'].generate_summary.return_value = "Tech > Finance"
        
        with patch('src.multi_market_scheduler.DataFetcherFactory') as mock_factory:
            mock_fetcher = Mock()
            mock_fetcher.get_sector_data.return_value = mock_df
            mock_factory.create.return_value = mock_fetcher
            
            result = await scheduler.run_single_market('a_share')
        
        assert result['market'] == 'a_share'
        assert result['success'] is True
        assert result['top10'] is not None
        assert len(result['rotation_signals']) == 0
    
    @pytest.mark.asyncio
    async def test_run_single_market_failure(self, scheduler, mock_components):
        """测试运行单个市场失败"""
        with patch('src.multi_market_scheduler.DataFetcherFactory') as mock_factory:
            mock_fetcher = Mock()
            mock_fetcher.get_sector_data.side_effect = Exception("网络错误")
            mock_factory.create.return_value = mock_fetcher
            
            result = await scheduler.run_single_market('us')
        
        assert result['market'] == 'us'
        assert result['success'] is False
        assert 'error' in result
        assert '网络错误' in result['error']
    
    @pytest.mark.asyncio
    async def test_run_all_markets(self, scheduler, mock_components):
        """测试运行所有市场"""
        mock_df = pd.DataFrame({
            'sector_name': ['Sector1'],
            'change_pct': [1.0],
            'main_inflow': [1000000],
        })
        
        mock_components['analyzer'].rank_by_inflow.return_value = mock_df
        mock_components['analyzer'].get_last_trading_date.return_value = '2024-01-01'
        mock_components['analyzer'].detect_rotation.return_value = []
        mock_components['reporter'].generate_summary.return_value = "Sector1"
        
        # 禁用港股
        scheduler.schedules['hk'].enabled = False
        
        with patch('src.multi_market_scheduler.DataFetcherFactory') as mock_factory:
            mock_fetcher = Mock()
            mock_fetcher.get_sector_data.return_value = mock_df
            mock_factory.create.return_value = mock_fetcher
            
            results = await scheduler.run_all_markets()
        
        assert 'a_share' in results
        assert 'us' in results
        assert 'hk' in results
        assert results['a_share']['success'] is True
        assert results['us']['success'] is True
        assert results['hk'].get('skipped') is True  # 被跳过
    
    @pytest.mark.asyncio
    async def test_generate_multi_market_report(self, scheduler, mock_components):
        """测试生成多市场报告"""
        results = {
            'a_share': {
                'success': True,
                'top10': pd.DataFrame({
                    'sector_name': ['Tech'],
                    'change_pct': [2.0],
                    'main_inflow': [1000000],
                }),
                'rotation_signals': [],
            },
            'us': {
                'success': True,
                'top10': pd.DataFrame({
                    'sector_name': ['XLK'],
                    'symbol': ['Technology'],
                    'change_pct': [1.5],
                    'main_inflow': [500000],
                }),
                'rotation_signals': [{'sector_name': 'XLK', 'yesterday_rank': 15}],
            },
        }
        
        mock_components['reporter'].generate_multi_markdown.return_value = "# 报告内容"
        
        with patch.object(scheduler, '_save_market_snapshot'):
            await scheduler._generate_multi_market_report(results)
        
        # 验证报告生成被调用
        mock_components['reporter'].generate_multi_markdown.assert_called_once()
    
    def test_update_schedule(self, scheduler):
        """测试更新调度配置"""
        # 更新时间
        scheduler.update_schedule('a_share', schedule_time='14:30')
        assert scheduler.schedules['a_share'].schedule_time == '14:30'
        
        # 更新启用状态
        scheduler.update_schedule('us', enabled=False)
        assert scheduler.schedules['us'].enabled is False
        
        # 同时更新
        scheduler.update_schedule('hk', schedule_time='17:00', enabled=True)
        assert scheduler.schedules['hk'].schedule_time == '17:00'
        assert scheduler.schedules['hk'].enabled is True
    
    def test_update_schedule_invalid_market(self, scheduler):
        """测试更新无效市场的调度配置"""
        with pytest.raises(ValueError) as exc_info:
            scheduler.update_schedule('invalid_market', schedule_time='10:00')
        assert "未知市场" in str(exc_info.value)
    
    def test_get_last_trade_date_a_share(self, scheduler):
        """测试获取A股上一个交易日"""
        # 周二的上一个交易日是周一
        result = scheduler._get_last_trade_date('a_share', '2024-01-09')
        assert result == '2024-01-08'
        
        # 周一的上一个交易日是上周五
        result = scheduler._get_last_trade_date('a_share', '2024-01-08')
        assert result == '2024-01-05'
    
    def test_get_last_trade_date_us(self, scheduler):
        """测试获取美股上一个交易日"""
        # 美股周二的上一个交易日是周一
        result = scheduler._get_last_trade_date('us', '2024-01-09')
        assert result == '2024-01-08'
        
        # 美股周一的上一个交易日是上周五（美股周五收盘后）
        result = scheduler._get_last_trade_date('us', '2024-01-08')
        assert result == '2024-01-05'
    
    def test_get_fetcher_caching(self, scheduler):
        """测试数据获取器缓存"""
        with patch('src.multi_market_scheduler.DataFetcherFactory') as mock_factory:
            mock_fetcher = Mock()
            mock_factory.create.return_value = mock_fetcher
            
            # 第一次获取
            fetcher1 = scheduler._get_fetcher('a_share')
            # 第二次获取（应该从缓存）
            fetcher2 = scheduler._get_fetcher('a_share')
            
            # 验证工厂只被调用一次
            mock_factory.create.assert_called_once()
            assert fetcher1 is fetcher2


class TestMultiMarketIntegration:
    """多市场集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建真实组件
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = SectorAnalyzer(data_path=tmpdir)
            reporter = ReportGenerator()
            
            scheduler = MultiMarketScheduler(
                analyzer=analyzer,
                reporter=reporter,
                output_mode='notion'
            )
            
            # 禁用所有市场，只测试A股
            for key in scheduler.schedules:
                scheduler.schedules[key].enabled = False
            scheduler.schedules['a_share'].enabled = True
            
            # 模拟数据获取
            mock_df = pd.DataFrame({
                'sector_name': ['半导体', '白酒'],
                'change_pct': [2.5, -1.0],
                'main_inflow': [500000000, -200000000],
            })
            
            with patch('src.multi_market_scheduler.DataFetcherFactory') as mock_factory:
                mock_fetcher = Mock()
                mock_fetcher.get_sector_data.return_value = mock_df
                mock_factory.create.return_value = mock_fetcher
                
                result = await scheduler.run_single_market('a_share')
            
            assert result['success'] is True
            assert result['top10'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
