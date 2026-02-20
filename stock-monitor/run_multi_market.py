#!/usr/bin/env python3
"""
多市场股票板块监控 - 快速运行脚本

使用方法:
    python run_multi_market.py              # 立即运行一次（默认）
    python run_multi_market.py --market us  # 只运行美股
    python run_multi_market.py --market hk  # 只运行港股
    python run_multi_market.py --market a_share  # 只运行A股
    python run_multi_market.py --all        # 运行所有市场
"""
import logging
import sys
import asyncio
import argparse
from datetime import datetime

# 添加 src 到路径
sys.path.insert(0, '.')

from src.config import get_settings
from src.analyzer import SectorAnalyzer
from src.reporter import ReportGenerator
from src.notion_writer import NotionWriter
from src.chart_generator import ChartGenerator
from src.image_uploader import ImageUploader
from src.multi_market_scheduler import MultiMarketScheduler


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


async def run_market(scheduler: MultiMarketScheduler, market: str):
    """运行单个市场"""
    logger = logging.getLogger(__name__)
    logger.info(f"\n{'='*60}")
    logger.info(f"开始运行 {market.upper()} 市场监控")
    logger.info('='*60)
    
    result = await scheduler.run_single_market(market)
    
    if result.get('success'):
        logger.info(f"✅ {market.upper()} 市场运行成功")
        
        # 写入 Notion 报告
        if scheduler.output_mode in ("notion", "both") and scheduler.notion_writer:
            try:
                from datetime import datetime
                
                # 构建单市场报告
                market_names = {'a_share': 'A股', 'us': '美股', 'hk': '港股'}
                market_display = market_names.get(market, market)
                
                # 生成 Markdown 报告
                report = scheduler.reporter.generate_single_market_markdown(market, result, market_display)
                
                # 解析 Markdown 为 blocks
                blocks = scheduler.notion_writer._parse_markdown_to_blocks(report)
                
                # 添加图表（如果有）
                chart_files = result.get('chart_files', [])
                if chart_files:
                    chart_blocks = scheduler.notion_writer._create_simple_chart_blocks(chart_files)
                    if chart_blocks:
                        blocks.extend(chart_blocks)
                
                # 创建页面
                title = f"📊 {market_display}板块监控 - {datetime.now().strftime('%Y-%m-%d')}"
                page_id = scheduler.notion_writer._create_page(title, blocks)
                
                if page_id:
                    logger.info(f"📄 Notion页面已创建: https://notion.so/{page_id.replace('-', '')}")
                else:
                    logger.warning("⚠️ Notion页面创建失败")
                    
            except Exception as e:
                logger.error(f"❌ 写入Notion失败: {e}")
        
        if 'page_url' in result:
            logger.info(f"📄 Notion页面: {result['page_url']}")
    else:
        logger.error(f"❌ {market.upper()} 市场运行失败: {result.get('error', '未知错误')}")
    
    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多市场板块资金流向监控')
    parser.add_argument('--market', choices=['a_share', 'us', 'hk'], 
                       help='指定运行单个市场')
    parser.add_argument('--all', action='store_true', 
                       help='运行所有启用的市场')
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 获取配置
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("多市场板块资金流向监控系统")
    logger.info("=" * 60)
    
    # 检查 Notion 配置
    if not settings.NOTION_API_KEY or not settings.NOTION_PARENT_PAGE_ID:
        logger.error("❌ 请先配置 NOTION_API_KEY 和 NOTION_PARENT_PAGE_ID")
        logger.error("   编辑 .env 文件添加以下配置:")
        logger.error("   NOTION_API_KEY=你的API密钥")
        logger.error("   NOTION_PARENT_PAGE_ID=你的页面ID")
        sys.exit(1)
    
    # 初始化组件
    logger.info("初始化组件...")
    
    analyzer = SectorAnalyzer(data_path=settings.DATA_PATH)
    reporter = ReportGenerator()
    
    notion_writer = NotionWriter(
        api_key=settings.NOTION_API_KEY,
        parent_page_id=settings.NOTION_PARENT_PAGE_ID
    )
    notion_writer.database_id = settings.NOTION_DATABASE_ID
    
    # 测试连接
    if not notion_writer.test_connection():
        logger.error("❌ Notion API连接测试失败")
        sys.exit(1)
    logger.info("✅ Notion连接测试通过")
    
    chart_generator = ChartGenerator(
        data_path=settings.DATA_PATH,
        charts_path="./charts"
    )
    logger.info("✅ 图表生成器已初始化")
    
    scheduler = MultiMarketScheduler(
        analyzer=analyzer,
        reporter=reporter,
        notion_writer=notion_writer,
        chart_generator=chart_generator,
        output_mode="notion"
    )
    
    logger.info("✅ 调度器已初始化")
    logger.info("")
    
    # 运行指定市场
    if args.market:
        result = await run_market(scheduler, args.market)
        success = result.get('success', False)
    elif args.all:
        logger.info("运行所有启用的市场...")
        results = await scheduler.run_all_markets()
        success = any(r.get('success', False) for r in results.values())
    else:
        # 默认运行美股（方便测试）
        logger.info("未指定市场，默认运行美股...")
        result = await run_market(scheduler, 'us')
        success = result.get('success', False)
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ 任务执行完成")
    else:
        logger.error("❌ 任务执行失败")
    logger.info("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
