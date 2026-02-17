"""TelegramNotifier模块测试"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from telegram.error import TelegramError, NetworkError
from src.notifier import TelegramNotifier


class TestTelegramNotifier:
    """TelegramNotifier通知器测试"""
    
    @pytest.fixture
    def notifier(self):
        with patch('src.notifier.Bot') as MockBot:
            mock_bot = MagicMock()
            MockBot.return_value = mock_bot
            notifier = TelegramNotifier(
                bot_token="test_token_12345",
                chat_id="123456789"
            )
            notifier.bot = mock_bot
            yield notifier
    
    @pytest.mark.asyncio
    async def test_send_report_success(self, notifier):
        """测试发送消息成功"""
        notifier.bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
        
        result = await notifier.send_report("测试消息")
        
        assert result is True
        notifier.bot.send_message.assert_called_once()
        # 验证调用参数
        call_args = notifier.bot.send_message.call_args
        assert call_args.kwargs['chat_id'] == "123456789"
        assert call_args.kwargs['text'] == "测试消息"
    
    @pytest.mark.asyncio
    async def test_send_report_with_markdown(self, notifier):
        """测试发送Markdown格式消息"""
        notifier.bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
        markdown_msg = "**粗体** 和 _斜体_"
        
        await notifier.send_report(markdown_msg)
        
        notifier.bot.send_message.assert_called_once()
        call_args = notifier.bot.send_message.call_args
        assert call_args.kwargs['parse_mode'] is not None
    
    @pytest.mark.asyncio
    async def test_send_report_network_error(self, notifier):
        """测试网络超时处理"""
        notifier.bot.send_message = AsyncMock(side_effect=NetworkError("Connection timeout"))
        
        with pytest.raises(NetworkError):
            await notifier.send_report("测试消息")
    
    @pytest.mark.asyncio
    async def test_send_report_telegram_error(self, notifier):
        """测试Telegram API错误处理"""
        notifier.bot.send_message = AsyncMock(side_effect=TelegramError("Invalid token"))
        
        with pytest.raises(TelegramError):
            await notifier.send_report("测试消息")
    
    @pytest.mark.asyncio
    async def test_send_report_generic_error(self, notifier):
        """测试一般错误处理"""
        notifier.bot.send_message = AsyncMock(side_effect=Exception("Some unexpected error"))
        
        result = await notifier.send_report("测试消息")
        
        # 一般错误返回False而不是抛出异常
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_test_message(self, notifier):
        """测试发送测试消息"""
        notifier.bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
        
        result = await notifier.send_test_message()
        
        assert result is True
        notifier.bot.send_message.assert_called_once()
        # 验证消息内容包含启动信息
        call_args = notifier.bot.send_message.call_args
        assert '已启动' in call_args.kwargs['text']
    
    @pytest.mark.asyncio
    async def test_send_long_message(self, notifier):
        """测试发送长消息"""
        notifier.bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
        long_message = "A" * 1000
        
        result = await notifier.send_report(long_message)
        
        assert result is True
        notifier.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_with_special_chars(self, notifier):
        """测试发送含特殊字符的消息"""
        notifier.bot.send_message = AsyncMock(return_value=MagicMock(message_id=123))
        special_msg = "测试中文 🔥 和表情 📊 以及特殊字符 <>&"
        
        result = await notifier.send_report(special_msg)
        
        assert result is True
        call_args = notifier.bot.send_message.call_args
        assert call_args.kwargs['disable_web_page_preview'] is True
    
    def test_notifier_init(self):
        """测试初始化"""
        with patch('src.notifier.Bot') as MockBot:
            mock_bot = MagicMock()
            MockBot.return_value = mock_bot
            notifier = TelegramNotifier(
                bot_token="my_custom_token",
                chat_id="987654321"
            )
            
            assert notifier.bot_token == "my_custom_token"
            assert notifier.chat_id == "987654321"
            assert notifier.bot is not None
    
    @pytest.mark.asyncio
    async def test_send_report_rate_limit(self, notifier):
        """测试速率限制错误"""
        notifier.bot.send_message = AsyncMock(side_effect=TelegramError("Too Many Requests: retry after 30"))
        
        with pytest.raises(TelegramError):
            await notifier.send_report("测试消息")
