"""通知模块 - Telegram推送"""
import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError, NetworkError

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram通知器类"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot = Bot(token=bot_token)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def send_report(self, message: str) -> bool:
        """
        异步发送报告到Telegram
        
        Args:
            message: Markdown格式的消息
            
        Returns:
            bool: 发送是否成功
            
        Raises:
            NetworkError: 网络超时
            TelegramError: API错误
        """
        try:
            self.logger.info(f"正在发送消息到 Telegram (chat_id: {self.chat_id})...")
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            
            self.logger.info("消息发送成功")
            return True
            
        except NetworkError as e:
            self.logger.error(f"网络错误，发送失败: {str(e)}")
            raise NetworkError(f"发送消息网络超时: {str(e)}")
            
        except TelegramError as e:
            self.logger.error(f"Telegram API错误: {str(e)}")
            raise TelegramError(f"Telegram API错误: {str(e)}")
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {str(e)}")
            return False
    
    async def send_test_message(self) -> bool:
        """
        发送测试消息
        
        Returns:
            bool: 发送是否成功
        """
        test_msg = "🤖 股票板块监控机器人已启动！\n\n正在监控A股板块资金流向..."
        return await self.send_report(test_msg)
