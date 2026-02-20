#!/usr/bin/env python3
"""
股票板块轮动监控 - 主入口

⚠️ 已弃用: 此入口仅支持A股，已被 run_multi_market.py 替代
   请使用: python run_multi_market.py --market a_share
   或: python run_multi_market.py --all (运行所有市场)

使用方法:
    python main.py           # 启动定时调度
    python main.py --run-once  # 立即运行一次
    python main.py --init-notion  # 初始化Notion数据库
"""
import logging
import sys
import asyncio
import argparse
from datetime import datetime

from src.config import get_settings
from src.data_fetchers import DataFetcherFactory, MarketType
from src.analyzer import SectorAnalyzer
from src.reporter import ReportGenerator
from src.notifier import TelegramNotifier
from src.notion_writer import NotionWriter
from src.chart_generator import ChartGenerator
from src.image_uploader import ImageUploader
from src.scheduler import MonitorScheduler


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='A股板块资金流向监控工具'
    )
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='立即运行一次，不启动定时调度'
    )
    parser.add_argument(
        '--test-notify',
        action='store_true',
        help='发送测试消息到Telegram'
    )
    parser.add_argument(
        '--init-notion',
        action='store_true',
        help='初始化Notion数据库'
    )
    parser.add_argument(
        '--output-mode',
        choices=['telegram', 'notion', 'both'],
        default=None,
        help='输出模式: telegram, notion, both (覆盖配置)'
    )
    return parser.parse_args()


async def main():
    """主函数"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    args = parse_args()
    
    # 获取配置
    settings = get_settings()
    
    # 确定输出模式
    output_mode = args.output_mode or settings.OUTPUT_MODE
    
    logger.info("=" * 50)
    logger.info("A股板块资金流向监控系统")
    logger.info(f"输出模式: {output_mode}")
    logger.info("=" * 50)
    
    # 初始化Notion数据库模式
    if args.init_notion:
        if not settings.NOTION_API_KEY or not settings.NOTION_PARENT_PAGE_ID:
            logger.error("请先配置 NOTION_API_KEY 和 NOTION_PARENT_PAGE_ID")
            sys.exit(1)
        
        logger.info("初始化Notion数据库...")
        notion_writer = NotionWriter(
            api_key=settings.NOTION_API_KEY,
            parent_page_id=settings.NOTION_PARENT_PAGE_ID
        )
        
        # 测试连接
        if not notion_writer.test_connection():
            logger.error("Notion API连接测试失败")
            sys.exit(1)
        
        # 创建数据库
        db_id = notion_writer.create_monitoring_database("板块监控记录")
        if db_id:
            logger.info(f"数据库创建成功！ID: {db_id}")
            logger.info(f"请将以下ID添加到 .env 文件的 NOTION_DATABASE_ID 变量:")
            logger.info(f"NOTION_DATABASE_ID={db_id}")
        else:
            logger.error("数据库创建失败")
            sys.exit(1)
        return
    
    # 初始化组件
    logger.info("初始化组件...")
    
    try:
        data_fetcher = DataFetcher()
        analyzer = SectorAnalyzer(data_path=settings.DATA_PATH)
        reporter = ReportGenerator()
        
        # 初始化输出组件
        notifier = None
        notion_writer = None
        chart_generator = None
        image_uploader = None
        
        if output_mode in ("telegram", "both"):
            if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
                logger.error("Telegram模式需要配置 TELEGRAM_BOT_TOKEN 和 TELEGRAM_CHAT_ID")
                sys.exit(1)
            notifier = TelegramNotifier(
                bot_token=settings.TELEGRAM_BOT_TOKEN,
                chat_id=settings.TELEGRAM_CHAT_ID
            )
            logger.info("Telegram通知器已初始化")
        
        if output_mode in ("notion", "both"):
            if not settings.NOTION_API_KEY or not settings.NOTION_PARENT_PAGE_ID:
                logger.error("Notion模式需要配置 NOTION_API_KEY 和 NOTION_PARENT_PAGE_ID")
                sys.exit(1)
            notion_writer = NotionWriter(
                api_key=settings.NOTION_API_KEY,
                parent_page_id=settings.NOTION_PARENT_PAGE_ID
            )
            notion_writer.database_id = settings.NOTION_DATABASE_ID
            
            # 测试连接
            if not notion_writer.test_connection():
                logger.error("Notion API连接测试失败")
                sys.exit(1)
            
            logger.info("Notion写入器已初始化")
            
            # 初始化图表生成器
            chart_generator = ChartGenerator(
                data_path=settings.DATA_PATH,
                charts_path="./charts"
            )
            logger.info("图表生成器已初始化")
            
            # 初始化图片上传器（Imgur可选，仅用于兼容旧版或需要外部URL的场景）
            # 新版已支持直接上传图片到Notion，无需Imgur配置
            if settings.IMGUR_CLIENT_ID:
                image_uploader = ImageUploader(imgur_client_id=settings.IMGUR_CLIENT_ID)
                if image_uploader.test_imgur_connection():
                    logger.info("Imgur上传器已初始化（可选，用于外部URL）")
                else:
                    logger.warning("Imgur连接测试失败，将使用Notion直接上传")
                    image_uploader = None
        
        scheduler = MonitorScheduler(
            data_fetcher=data_fetcher,
            analyzer=analyzer,
            reporter=reporter,
            notifier=notifier,
            notion_writer=notion_writer,
            chart_generator=chart_generator,
            image_uploader=image_uploader,
            schedule_time=settings.SCHEDULE_TIME,
            output_mode=output_mode
        )
        
        logger.info("组件初始化完成")
        
    except Exception as e:
        logger.error(f"组件初始化失败: {str(e)}")
        sys.exit(1)
    
    # 测试模式：发送测试消息
    if args.test_notify:
        logger.info("发送测试消息...")
        try:
            if notifier:
                await notifier.send_test_message()
                logger.info("Telegram测试消息发送成功")
            if notion_writer:
                notion_writer.write_report(
                    title="测试报告",
                    content="🧪 Notion写入测试成功！\n\n监控服务已启动。"
                )
                logger.info("Notion测试页面创建成功")
        except Exception as e:
            logger.error(f"测试消息发送失败: {str(e)}")
        return
    
    # 立即运行一次
    if args.run_once:
        logger.info("执行单次监控任务...")
        success = await scheduler.run_once()
        if success:
            logger.info("任务执行成功")
            sys.exit(0)
        else:
            logger.error("任务执行失败")
            sys.exit(1)
    
    # 启动定时调度
    else:
        logger.info(f"启动定时调度，将在每个交易日 {settings.SCHEDULE_TIME} 执行")
        
        # 发送启动通知
        try:
            startup_msg = (
                f"🚀 股票板块监控系统已启动\n"
                f"⏰ 调度时间：每个交易日 {settings.SCHEDULE_TIME}\n"
                f"📅 启动时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"📤 输出模式：{output_mode}"
            )
            if notifier:
                await notifier.send_report(startup_msg)
            if notion_writer:
                notion_writer.write_report(
                    title=f"系统启动 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    content=startup_msg
                )
        except Exception as e:
            logger.warning(f"发送启动通知失败: {str(e)}")
        
        # 启动调度器
        scheduler.start()
        
        # 保持运行
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到中断信号，正在停止...")
            scheduler.stop()
            logger.info("系统已停止")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
