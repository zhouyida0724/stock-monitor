"""
调度器模块 - APScheduler定时任务

⚠️ 已弃用: 此模块仅支持A股，已被 multi_market_scheduler.py 替代
   请使用: from src.multi_market_scheduler import MultiMarketScheduler
"""
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Optional, Union

from .data_fetchers import DataFetcherFactory, MarketType, BaseDataFetcher
from .analyzer import SectorAnalyzer
from .reporter import ReportGenerator
from .notifier import TelegramNotifier
from .notion_writer import NotionWriter
from .chart_generator import ChartGenerator
from .image_uploader import ImageUploader

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """监控调度器类"""
    
    def __init__(
        self,
        data_fetcher: BaseDataFetcher,
        analyzer: SectorAnalyzer,
        reporter: ReportGenerator,
        notifier: Optional[TelegramNotifier] = None,
        notion_writer: Optional[NotionWriter] = None,
        chart_generator: Optional[ChartGenerator] = None,
        image_uploader: Optional[ImageUploader] = None,
        schedule_time: str = "15:05",
        output_mode: str = "notion"
    ):
        self.data_fetcher = data_fetcher
        self.analyzer = analyzer
        self.reporter = reporter
        self.notifier = notifier
        self.notion_writer = notion_writer
        self.chart_generator = chart_generator
        self.image_uploader = image_uploader
        self.output_mode = output_mode
        self.schedule_time = schedule_time
        
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 解析时间 (格式: HH:MM)
        try:
            hour, minute = map(int, schedule_time.split(':'))
            self.schedule_hour = hour
            self.schedule_minute = minute
        except ValueError:
            self.logger.warning(f"无效的时间格式: {schedule_time}, 使用默认 15:05")
            self.schedule_hour = 15
            self.schedule_minute = 5
    
    async def run_once(self) -> bool:
        """
        单次运行完整流程
        
        Returns:
            bool: 运行是否成功
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self.logger.info(f"=== 开始执行板块监控任务 [{today}] ===")
        
        try:
            # 1. 获取今日数据
            self.logger.info("步骤 1/5: 获取板块资金流数据...")
            today_df = self.data_fetcher.get_sector_data(today)
            
            # 2. 计算排名
            self.logger.info("步骤 2/5: 计算TOP10排名...")
            top10_df = self.analyzer.rank_by_inflow(today_df, top_n=10)
            
            # 输出简要信息
            summary = self.reporter.generate_summary(top10_df)
            self.logger.info(f"今日TOP3: {summary}")
            
            # 3. 保存数据
            self.logger.info("步骤 3/5: 保存数据快照...")
            self.analyzer.save_snapshot(today_df, today)
            
            # 4. 检测轮动
            self.logger.info("步骤 4/5: 检测板块轮动...")
            
            # 获取上一个交易日
            last_trade_date = self.analyzer.get_last_trading_date(today)
            yesterday_df = self.analyzer.load_snapshot(last_trade_date)
            
            if yesterday_df is not None:
                yesterday_top10 = self.analyzer.rank_by_inflow(yesterday_df, top_n=20)
                rotation_signals = self.analyzer.detect_rotation(top10_df, yesterday_top10)
            else:
                self.logger.warning(f"未找到昨日数据 ({last_trade_date})，跳过轮动检测")
                rotation_signals = []
            
            # 5. 生成图表（如果有足够历史数据）
            chart_files = []
            if self.chart_generator:
                self.logger.info("步骤 5/6: 生成时间序列图表...")
                try:
                    # 生成TOP板块趋势图
                    trend_chart = self.chart_generator.generate_top_sectors_trend(top_n=5, days=14)
                    if trend_chart:
                        chart_files.append(trend_chart)
                    
                    # 生成热力图（如果有足够数据）
                    heatmap_chart = self.chart_generator.generate_market_heatmap(days=5)
                    if heatmap_chart:
                        chart_files.append(heatmap_chart)
                    
                    # 清理旧图表
                    self.chart_generator.cleanup_old_charts(keep_days=7)
                    
                except Exception as e:
                    self.logger.warning(f"生成图表失败: {e}")
            
            # 6. 上传图表到图床（如果配置了）
            chart_urls = []
            if self.image_uploader and chart_files:
                self.logger.info("上传图表到图床...")
                for chart_file in chart_files:
                    url = self.image_uploader.upload_to_imgur(chart_file)
                    if url:
                        chart_urls.append(url)
            
            # 7. 生成并发送报告
            self.logger.info("步骤 7/7: 生成并发送报告...")
            report = self.reporter.generate_markdown(top10_df, rotation_signals)
            
            # 根据输出模式选择发送方式
            if self.output_mode in ("telegram", "both") and self.notifier:
                await self.notifier.send_report(report)
            
            if self.output_mode in ("notion", "both") and self.notion_writer:
                title = f"板块资金流向监控 - {today}"
                db_id = getattr(self.notion_writer, 'database_id', None)
                self.notion_writer.write_report(
                    title, report, 
                    database_id=db_id, 
                    chart_files=chart_files,
                    chart_urls=chart_urls
                )
            
            self.logger.info("=== 任务执行完成 ===")
            return True
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {str(e)}", exc_info=True)
            
            # 发送错误通知
            error_msg = f"❌ 监控任务执行失败\n\n错误信息: {str(e)}\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                if self.output_mode in ("telegram", "both") and self.notifier:
                    await self.notifier.send_report(error_msg)
                if self.output_mode in ("notion", "both") and self.notion_writer:
                    title = f"监控异常 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    self.notion_writer.write_report(title, error_msg)
            except:
                pass
                
            return False
    
    def start(self):
        """启动定时调度（交易日运行）"""
        self.logger.info(f"启动定时调度器，每日 {self.schedule_time} 执行（工作日）")
        
        # 添加定时任务：周一至周五执行
        trigger = CronTrigger(
            hour=self.schedule_hour,
            minute=self.schedule_minute,
            day_of_week='mon-fri'
        )
        
        self.scheduler.add_job(
            self.run_once,
            trigger=trigger,
            id='sector_monitor',
            name='板块资金流向监控',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.logger.info("调度器已启动，等待定时任务...")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        self.logger.info("调度器已停止")
