"""多市场调度器模块 - 支持A股/美股/港股独立调度"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .data_fetchers import DataFetcherFactory, MarketType
from .analyzer import SectorAnalyzer
from .reporter import ReportGenerator
from .notifier import TelegramNotifier
from .notion_writer import NotionWriter
from .chart_generator import ChartGenerator
from .image_uploader import ImageUploader
from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class MarketSchedule:
    """市场调度配置"""
    market: str
    enabled: bool
    schedule_time: str  # 格式: HH:MM
    days_of_week: str   # 格式: mon-fri 或 *


class MultiMarketScheduler:
    """多市场监控调度器

    支持A股、美股、港股的独立调度配置
    每个市场可以设置不同的运行时间和交易日
    """

    # 默认调度配置
    DEFAULT_SCHEDULES = {
        'a_share': MarketSchedule(
            market='a_share',
            enabled=True,
            schedule_time='15:05',
            days_of_week='mon-fri'
        ),
        'us': MarketSchedule(
            market='us',
            enabled=True,
            schedule_time='06:00',  # 美股收盘后（北京时间早上）
            days_of_week='tue-sat'  # 美股周一至周五收盘
        ),
        'hk': MarketSchedule(
            market='hk',
            enabled=True,
            schedule_time='16:05',  # 港股收盘后
            days_of_week='mon-fri'
        ),
    }

    def __init__(
        self,
        analyzer: SectorAnalyzer,
        reporter: ReportGenerator,
        notifier: Optional[TelegramNotifier] = None,
        notion_writer: Optional[NotionWriter] = None,
        chart_generator: Optional[ChartGenerator] = None,
        image_uploader: Optional[ImageUploader] = None,
        output_mode: str = "notion",
        schedules: Optional[Dict[str, MarketSchedule]] = None
    ):
        self.analyzer = analyzer
        self.reporter = reporter
        self.notifier = notifier
        self.notion_writer = notion_writer
        self.chart_generator = chart_generator
        self.image_uploader = image_uploader
        self.output_mode = output_mode

        # 调度配置
        self.schedules = schedules or self.DEFAULT_SCHEDULES.copy()

        # 缓存的数据获取器
        self._fetchers: Dict[str, any] = {}

        # APScheduler
        self.scheduler = AsyncIOScheduler()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_fetcher(self, market: str):
        """获取或创建数据获取器"""
        if market not in self._fetchers:
            self._fetchers[market] = DataFetcherFactory.create(market)
        return self._fetchers[market]

    async def run_single_market(self, market: str) -> Dict:
        """运行单个市场的监控任务（增强版：包含完整数据用于图表生成）

        Args:
            market: 市场类型 ('a_share', 'us', 'hk')

        Returns:
            Dict: 运行结果，包含完整数据
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self.logger.info(f"=== 开始执行 {market.upper()} 板块监控 [{today}] ===")

        result = {
            'market': market,
            'success': False,
            'top10': None,
            'full_data': None,  # 新增：完整数据
            'rotation_signals': [],
            'error': None,
            'chart_files': []   # 新增：该市场生成的图表
        }

        try:
            # 1. 获取数据获取器
            fetcher = self._get_fetcher(market)

            # 2. 获取板块数据
            self.logger.info(f"[{market}] 步骤 1/5: 获取板块数据...")
            today_df = fetcher.get_sector_data(today)

            if today_df is None or today_df.empty:
                result['error'] = "获取数据为空"
                return result

            # 保存完整数据
            result['full_data'] = today_df

            # 3. 计算排名
            self.logger.info(f"[{market}] 步骤 2/5: 计算TOP10排名...")
            top10_df = self.analyzer.rank_by_inflow(today_df, top_n=10)
            result['top10'] = top10_df

            # 输出简要信息
            summary = self.reporter.generate_summary(top10_df)
            self.logger.info(f"[{market}] 今日TOP3: {summary}")

            # 4. 保存数据（使用市场前缀区分）
            self.logger.info(f"[{market}] 步骤 3/5: 保存数据快照...")
            self._save_market_snapshot(today_df, today, market)

            # 5. 检测轮动
            self.logger.info(f"[{market}] 步骤 4/5: 检测板块轮动...")
            last_trade_date = self._get_last_trade_date(market, today)
            yesterday_df = self._load_market_snapshot(last_trade_date, market)

            if yesterday_df is not None:
                yesterday_top10 = self.analyzer.rank_by_inflow(yesterday_df, top_n=20)
                rotation_signals = self.analyzer.detect_rotation(top10_df, yesterday_top10)
                result['rotation_signals'] = rotation_signals
            else:
                self.logger.warning(f"[{market}] 未找到昨日数据 ({last_trade_date})，跳过轮动检测")
                rotation_signals = []

            # 6. 生成市场专属图表（新增）
            self.logger.info(f"[{market}] 步骤 5/5: 生成资金流向图表...")
            if self.chart_generator:
                chart_files = self._generate_market_charts(today_df, market)
                result['chart_files'] = chart_files

            result['success'] = True
            self.logger.info(f"=== {market.upper()} 任务执行完成 ===")

        except Exception as e:
            self.logger.error(f"[{market}] 任务执行失败: {str(e)}", exc_info=True)
            result['error'] = str(e)

        return result

    def _generate_market_charts(self, df: pd.DataFrame, market: str) -> List[str]:
        """为指定市场生成图表

        Args:
            df: 板块数据
            market: 市场类型

        Returns:
            List[str]: 生成的图表文件路径列表
        """
        chart_files = []
        market_names = {'a_share': 'A股', 'us': '美股', 'hk': '港股'}
        market_name = market_names.get(market, market)

        try:
            # 1. 生成饼图（净流入和净流出）
            self.logger.info(f"[{market}] 生成资金流向饼图...")
            pie_charts = self.chart_generator.generate_sector_flow_pie_charts(df, market_name)
            if pie_charts.get('inflow'):
                chart_files.append(pie_charts['inflow'])
            if pie_charts.get('outflow'):
                chart_files.append(pie_charts['outflow'])

            # 2. 生成整体资金流向摘要图
            self.logger.info(f"[{market}] 生成资金流向摘要图...")
            summary_chart = self.chart_generator.generate_market_flow_summary_chart(df, market_name)
            if summary_chart:
                chart_files.append(summary_chart)

            # 3. 生成趋势图（如果有足够历史数据）
            # 这里使用现有的趋势图生成方法
            # 可以后续根据需要扩展

            # 3. 生成趋势图（时序折线图）
            self.logger.info(f"[{market}] 生成TOP板块趋势图...")
            trend_chart = self.chart_generator.generate_market_top_sectors_trend(
                market_name=market_name,
                top_n=5,
                days=14
            )
            if trend_chart:
                chart_files.append(trend_chart)

        except Exception as e:
            self.logger.warning(f"[{market}] 生成图表失败: {e}")

        return chart_files

    async def run_all_markets(self) -> Dict[str, Dict]:
        """运行所有启用的市场监控任务

        Returns:
            Dict[str, Dict]: 各市场的运行结果
        """
        results = {}

        for market_key, schedule in self.schedules.items():
            if schedule.enabled:
                results[market_key] = await self.run_single_market(schedule.market)
            else:
                self.logger.info(f"市场 {market_key} 已禁用，跳过")
                results[market_key] = {'market': schedule.market, 'success': False, 'skipped': True}

        return results

    async def run_once(self) -> bool:
        """单次运行完整流程（多市场版本）

        Returns:
            bool: 是否有任何市场成功
        """
        today = datetime.now().strftime('%Y-%m-%d')
        self.logger.info(f"=== 开始执行多市场板块监控 [{today}] ===")

        # 运行所有市场
        results = await self.run_all_markets()

        # 检查是否有任何成功
        any_success = any(r.get('success', False) for r in results.values())

        if any_success:
            # 生成多市场报告
            await self._generate_multi_market_report(results)

        return any_success

    async def _generate_multi_market_report(self, results: Dict[str, Dict]):
        """生成多市场综合报告（图表紧跟在每个市场分析后）"""
        today = datetime.now().strftime('%Y-%m-%d')

        # 生成Markdown报告
        report = self.reporter.generate_multi_markdown(results)

        # 发送报告
        if self.output_mode in ("telegram", "both") and self.notifier:
            await self.notifier.send_report(report)

        if self.output_mode in ("notion", "both") and self.notion_writer:
            title = f"📊 多市场板块监控 - {today}"

            # 为每个市场准备图表映射
            market_chart_map = {}
            market_names = {'a_share': 'A股', 'us': '美股', 'hk': '港股'}

            for market, result in results.items():
                if result.get('success') and result.get('chart_files'):
                    market_chart_map[market] = result['chart_files']

            # 使用新的分市场图表上传方法
            self.notion_writer.write_report_with_market_charts(
                title, report,
                market_chart_map=market_chart_map,
                market_names=market_names
            )

    def _save_market_snapshot(self, df, date_str: str, market: str):
        """保存市场特定数据"""
        import os
        market_prefix = f"{market}_"

        # 确保目录存在
        data_path = self.analyzer.data_path
        os.makedirs(data_path, exist_ok=True)

        file_path = os.path.join(
            data_path,
            f"{market_prefix}sector_flow_{date_str.replace('-', '')}.csv"
        )
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        self.logger.info(f"[{market}] 数据已保存到: {file_path}")

    def _load_market_snapshot(self, date_str: str, market: str):
        """加载市场特定数据"""
        import os
        market_prefix = f"{market}_"
        file_path = os.path.join(
            self.analyzer.data_path,
            f"{market_prefix}sector_flow_{date_str.replace('-', '')}.csv"
        )
        if not os.path.exists(file_path):
            return None
        return pd.read_csv(file_path, encoding='utf-8-sig')

    def _get_last_trade_date(self, market: str, date_str: str) -> str:
        """获取指定市场的上一个交易日"""
        from datetime import datetime, timedelta

        date = datetime.strptime(date_str.replace('-', ''), '%Y%m%d')

        # 美股特殊处理：周一的上一个交易日是周五
        if market == 'us':
            if date.weekday() == 0:  # 周一
                prev_date = date - timedelta(days=3)
            else:
                prev_date = date - timedelta(days=1)
        else:
            # A股和港股：跳过周末
            for i in range(1, 10):
                prev_date = date - timedelta(days=i)
                if prev_date.weekday() < 5:
                    break

        return prev_date.strftime('%Y-%m-%d')

    def start(self):
        """启动多市场定时调度"""
        self.logger.info("启动多市场定时调度器")

        for market_key, schedule in self.schedules.items():
            if not schedule.enabled:
                self.logger.info(f"市场 {market_key} 已禁用")
                continue

            try:
                hour, minute = map(int, schedule.schedule_time.split(':'))
            except ValueError:
                self.logger.warning(f"[{market_key}] 无效的时间格式: {schedule.schedule_time}")
                continue

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=schedule.days_of_week
            )

            self.scheduler.add_job(
                self.run_single_market,
                trigger=trigger,
                id=f'sector_monitor_{market_key}',
                name=f'{market_key}板块监控',
                args=[schedule.market],
                replace_existing=True
            )

            self.logger.info(
                f"[{market_key}] 已调度: {schedule.schedule_time} "
                f"(星期: {schedule.days_of_week})"
            )

        self.scheduler.start()
        self.logger.info("多市场调度器已启动")

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        self.logger.info("多市场调度器已停止")

    def update_schedule(self, market: str, schedule_time: Optional[str] = None,
                       enabled: Optional[bool] = None):
        """更新市场调度配置

        Args:
            market: 市场类型
            schedule_time: 新的调度时间 (HH:MM)
            enabled: 是否启用
        """
        if market not in self.schedules:
            raise ValueError(f"未知市场: {market}")

        if schedule_time:
            self.schedules[market].schedule_time = schedule_time
        if enabled is not None:
            self.schedules[market].enabled = enabled

        self.logger.info(f"更新 {market} 调度配置: {self.schedules[market]}")
