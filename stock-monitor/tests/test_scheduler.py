"""MonitorScheduler模块测试"""
import pytest
import asyncio
import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from src.scheduler import MonitorScheduler


class TestMonitorScheduler:
    """MonitorScheduler调度器测试"""
    
    @pytest.fixture
    def scheduler(self, mock_scheduler_components):
        return MonitorScheduler(
            data_fetcher=mock_scheduler_components['data_fetcher'],
            analyzer=mock_scheduler_components['analyzer'],
            reporter=mock_scheduler_components['reporter'],
            notifier=mock_scheduler_components['notifier'],
            schedule_time="15:05",
            output_mode="telegram"
        )
    
    @pytest.mark.asyncio
    async def test_run_once_success(self, scheduler, mock_scheduler_components):
        """测试单次运行成功"""
        # 设置mock返回值
        mock_data = pd.DataFrame({'sector_name': ['A'], 'main_inflow': [100]})
        mock_scheduler_components['data_fetcher'].get_sector_flow.return_value = mock_data
        mock_scheduler_components['analyzer'].rank_by_inflow.return_value = mock_data
        mock_scheduler_components['analyzer'].get_last_trading_date.return_value = '2024-02-14'
        mock_scheduler_components['analyzer'].load_snapshot.return_value = mock_data
        mock_scheduler_components['analyzer'].detect_rotation.return_value = []
        mock_scheduler_components['reporter'].generate_markdown.return_value = "测试报告"
        mock_scheduler_components['reporter'].generate_summary.return_value = "A"
        mock_scheduler_components['notifier'].send_report = AsyncMock(return_value=True)
        
        result = await scheduler.run_once()
        
        assert result is True
        # 验证各组件被正确调用
        mock_scheduler_components['data_fetcher'].get_sector_flow.assert_called_once()
        mock_scheduler_components['analyzer'].rank_by_inflow.assert_called()
        mock_scheduler_components['analyzer'].save_snapshot.assert_called_once()
        mock_scheduler_components['notifier'].send_report.assert_called()
    
    @pytest.mark.asyncio
    async def test_run_once_data_fetch_error(self, scheduler, mock_scheduler_components):
        """测试数据获取失败"""
        mock_scheduler_components['data_fetcher'].get_sector_flow.side_effect = Exception("API Error")
        mock_scheduler_components['notifier'].send_report = AsyncMock(return_value=True)
        
        result = await scheduler.run_once()
        
        assert result is False
        mock_scheduler_components['notifier'].send_report.assert_called_once()
        # 验证错误消息被发送
        call_args = mock_scheduler_components['notifier'].send_report.call_args
        assert '失败' in call_args[0][0] or '错误' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_run_once_no_yesterday_data(self, scheduler, mock_scheduler_components):
        """测试无昨日数据的情况"""
        mock_data = pd.DataFrame({'sector_name': ['A'], 'main_inflow': [100]})
        mock_scheduler_components['data_fetcher'].get_sector_flow.return_value = mock_data
        mock_scheduler_components['analyzer'].rank_by_inflow.return_value = mock_data
        mock_scheduler_components['analyzer'].get_last_trading_date.return_value = '2024-02-14'
        mock_scheduler_components['analyzer'].load_snapshot.return_value = None  # 无昨日数据
        mock_scheduler_components['reporter'].generate_markdown.return_value = "测试报告"
        mock_scheduler_components['reporter'].generate_summary.return_value = "A"
        mock_scheduler_components['notifier'].send_report = AsyncMock(return_value=True)
        
        result = await scheduler.run_once()
        
        assert result is True
        # 应该跳过轮动检测
        mock_scheduler_components['analyzer'].detect_rotation.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_once_rotation_detected(self, scheduler, mock_scheduler_components):
        """测试检测到轮动信号"""
        mock_data = pd.DataFrame({'sector_name': ['A', 'B'], 'main_inflow': [100, 90]})
        rotation_signals = [{'sector_name': 'B', 'yesterday_rank': 15}]
        
        mock_scheduler_components['data_fetcher'].get_sector_flow.return_value = mock_data
        mock_scheduler_components['analyzer'].rank_by_inflow.return_value = mock_data
        mock_scheduler_components['analyzer'].get_last_trading_date.return_value = '2024-02-14'
        mock_scheduler_components['analyzer'].load_snapshot.return_value = mock_data
        mock_scheduler_components['analyzer'].detect_rotation.return_value = rotation_signals
        mock_scheduler_components['reporter'].generate_markdown.return_value = "测试报告"
        mock_scheduler_components['reporter'].generate_summary.return_value = "A"
        mock_scheduler_components['notifier'].send_report = AsyncMock(return_value=True)
        
        result = await scheduler.run_once()
        
        assert result is True
        mock_scheduler_components['analyzer'].detect_rotation.assert_called_once()
    
    def test_scheduler_init_default_time(self, mock_scheduler_components):
        """测试默认时间初始化"""
        scheduler = MonitorScheduler(
            data_fetcher=mock_scheduler_components['data_fetcher'],
            analyzer=mock_scheduler_components['analyzer'],
            reporter=mock_scheduler_components['reporter'],
            notifier=mock_scheduler_components['notifier']
        )
        
        assert scheduler.schedule_time == "15:05"
        assert scheduler.schedule_hour == 15
        assert scheduler.schedule_minute == 5
    
    def test_scheduler_init_custom_time(self, mock_scheduler_components):
        """测试自定义时间初始化"""
        scheduler = MonitorScheduler(
            data_fetcher=mock_scheduler_components['data_fetcher'],
            analyzer=mock_scheduler_components['analyzer'],
            reporter=mock_scheduler_components['reporter'],
            notifier=mock_scheduler_components['notifier'],
            schedule_time="09:30"
        )
        
        assert scheduler.schedule_time == "09:30"
        assert scheduler.schedule_hour == 9
        assert scheduler.schedule_minute == 30
    
    def test_scheduler_init_invalid_time(self, mock_scheduler_components):
        """测试无效时间格式初始化"""
        scheduler = MonitorScheduler(
            data_fetcher=mock_scheduler_components['data_fetcher'],
            analyzer=mock_scheduler_components['analyzer'],
            reporter=mock_scheduler_components['reporter'],
            notifier=mock_scheduler_components['notifier'],
            schedule_time="invalid"
        )
        
        # 应该回退到默认值
        assert scheduler.schedule_hour == 15
        assert scheduler.schedule_minute == 5
    
    @patch('src.scheduler.AsyncIOScheduler')
    def test_start_scheduler(self, mock_scheduler_class, scheduler):
        """测试启动定时调度"""
        mock_scheduler_instance = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        
        # 重新创建scheduler以使用mock的AsyncIOScheduler
        scheduler.scheduler = mock_scheduler_instance
        scheduler.start()
        
        mock_scheduler_instance.add_job.assert_called_once()
        mock_scheduler_instance.start.assert_called_once()
        
        # 验证调度参数
        call_kwargs = mock_scheduler_instance.add_job.call_args.kwargs
        assert call_kwargs['id'] == 'sector_monitor'
        assert call_kwargs['name'] == '板块资金流向监控'
    
    @patch('src.scheduler.AsyncIOScheduler')
    def test_stop_scheduler(self, mock_scheduler_class, scheduler):
        """测试停止调度器"""
        mock_scheduler_instance = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler_instance
        scheduler.scheduler = mock_scheduler_instance
        
        scheduler.stop()
        
        mock_scheduler_instance.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_once_notifier_error(self, scheduler, mock_scheduler_components):
        """测试通知发送失败"""
        mock_data = pd.DataFrame({'sector_name': ['A'], 'main_inflow': [100]})
        mock_scheduler_components['data_fetcher'].get_sector_flow.return_value = mock_data
        mock_scheduler_components['analyzer'].rank_by_inflow.return_value = mock_data
        mock_scheduler_components['analyzer'].get_last_trading_date.return_value = '2024-02-14'
        mock_scheduler_components['analyzer'].load_snapshot.return_value = None
        mock_scheduler_components['reporter'].generate_markdown.return_value = "测试报告"
        mock_scheduler_components['reporter'].generate_summary.return_value = "A"
        mock_scheduler_components['notifier'].send_report = AsyncMock(side_effect=Exception("Network error"))
        
        # 通知错误应该导致整体失败
        result = await scheduler.run_once()
        
        assert result is False
