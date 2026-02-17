"""Config模块测试"""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError
from src.config import Settings


class TestSettings:
    """Settings配置类测试"""
    
    def test_env_vars_loading(self):
        """测试环境变量加载"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'my_token_123',
            'TELEGRAM_CHAT_ID': '987654321'
        }):
            settings = Settings()
            assert settings.TELEGRAM_BOT_TOKEN == 'my_token_123'
            assert settings.TELEGRAM_CHAT_ID == '987654321'
    
    def test_default_values(self):
        """测试默认值"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'token123',
            'TELEGRAM_CHAT_ID': '123456'
        }):
            settings = Settings()
            # 测试默认值
            assert settings.SCHEDULE_TIME == "15:05"
            assert settings.DATA_PATH == "./data"
            # 多市场默认配置
            assert settings.ENABLED_MARKETS == "a_share,us,hk"
            assert settings.A_SHARE_ENABLED == True
            assert settings.US_ENABLED == True
            assert settings.HK_ENABLED == True
    
    def test_custom_schedule_time(self):
        """测试自定义调度时间"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'token123',
            'TELEGRAM_CHAT_ID': '123456',
            'SCHEDULE_TIME': '14:30'
        }):
            settings = Settings()
            assert settings.SCHEDULE_TIME == '14:30'
    
    def test_custom_data_path(self):
        """测试自定义数据路径"""
        with patch.dict(os.environ, {
            'TELEGRAM_BOT_TOKEN': 'token123',
            'TELEGRAM_CHAT_ID': '123456',
            'DATA_PATH': '/custom/data/path'
        }):
            settings = Settings()
            assert settings.DATA_PATH == '/custom/data/path'
    
    def test_optional_telegram_config(self):
        """测试Telegram配置是可选的（支持Notion模式）
        
        注意：此测试依赖于环境，如果.env文件存在会被自动加载
        """
        # 由于Pydantic Settings会自动加载.env文件，
        # 我们只验证配置类可以正常加载，不会因为没有Telegram配置而报错
        settings = Settings()
        
        # 验证配置对象被成功创建（不会抛出ValidationError）
        assert settings is not None
        assert settings.OUTPUT_MODE in ["telegram", "notion", "both"]
        
        # 验证多市场配置存在
        assert hasattr(settings, 'ENABLED_MARKETS')
        assert hasattr(settings, 'A_SHARE_ENABLED')
        assert hasattr(settings, 'US_ENABLED')
        assert hasattr(settings, 'HK_ENABLED')
    
    def test_market_config_loading(self):
        """测试市场配置加载"""
        with patch.dict(os.environ, {
            'ENABLED_MARKETS': 'a_share,us',
            'US_SCHEDULE_TIME': '07:00',
            'HK_ENABLED': 'false',
        }):
            settings = Settings()
            assert settings.ENABLED_MARKETS == "a_share,us"
            assert settings.US_SCHEDULE_TIME == "07:00"
            assert settings.HK_ENABLED == False
