"""图表生成模块 - 生成板块指标时间序列图"""
import logging
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict
import os

logger = logging.getLogger(__name__)


class ChartGenerator:
    """图表生成器类 - 生成板块资金流向时间序列图"""
    
    def __init__(self, data_path: str = "./data", charts_path: str = "./charts"):
        """
        初始化图表生成器
        
        Args:
            data_path: 历史数据存放路径
            charts_path: 图表输出路径
        """
        self.data_path = Path(data_path)
        self.charts_path = Path(charts_path)
        self.charts_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    
    def load_historical_data(self, days: int = 30, data_fetcher=None, sectors: List[str] = None) -> pd.DataFrame:
        """
        加载最近N天的历史数据

        优先从本地CSV加载，如果数据缺失且提供了data_fetcher，则从API获取补充数据

        Args:
            days: 加载天数
            data_fetcher: 可选，DataFetcher实例，用于从API获取缺失数据
            sectors: 可选，板块列表，用于API获取数据

        Returns:
            pd.DataFrame: 合并后的历史数据
        """
        all_data = []
        missing_dates = []

        # 首先尝试从本地CSV加载
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y%m%d')
            file_path = self.data_path / f"sector_flow_{date_str}.csv"

            if file_path.exists():
                try:
                    df = pd.read_csv(file_path)
                    df['date'] = date.strftime('%Y-%m-%d')
                    all_data.append(df)
                except Exception as e:
                    self.logger.warning(f"读取历史数据失败 {date_str}: {e}")
            else:
                # 记录缺失的日期（跳过周末）
                if date.weekday() < 5:  # 0-4 是周一到周五
                    missing_dates.append(date.strftime('%Y-%m-%d'))

        # 如果有缺失数据且提供了data_fetcher，尝试从API获取
        if missing_dates and data_fetcher and sectors:
            self.logger.info(f"尝试从API获取缺失数据: {len(missing_dates)} 天")
            try:
                for date_str in missing_dates[:5]:  # 限制API调用次数
                    # 尝试获取该日期的数据
                    df = data_fetcher.get_all_sectors_historical(sectors, days=1)
                    if not df.empty:
                        # 过滤特定日期
                        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                        day_data = df[df['date'] == date_str]
                        if not day_data.empty:
                            all_data.append(day_data)
                            # 保存到本地缓存
                            self._save_to_csv(day_data, date_str)
            except Exception as e:
                self.logger.warning(f"从API获取补充数据失败: {e}")

        if not all_data:
            self.logger.warning("未找到历史数据")
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"加载了 {len(all_data)} 天的数据，共 {len(combined)} 条记录")
        return combined

    def _save_to_csv(self, df: pd.DataFrame, date_str: str):
        """
        保存数据到CSV文件

        Args:
            df: DataFrame数据
            date_str: 日期字符串 YYYY-MM-DD
        """
        try:
            date_str_clean = date_str.replace('-', '')
            file_path = self.data_path / f"sector_flow_{date_str_clean}.csv"
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"数据已缓存到: {file_path}")
        except Exception as e:
            self.logger.warning(f"保存缓存数据失败: {e}")
    
    def generate_top_sectors_trend(self, top_n: int = 5, days: int = 14) -> str:
        """
        生成TOP板块资金流向趋势图
        
        Args:
            top_n: 显示前N个板块
            days: 显示最近N天
            
        Returns:
            str: 生成的图表文件路径
        """
        # 加载历史数据
        df = self.load_historical_data(days=days)
        
        if df.empty:
            self.logger.warning("无历史数据，无法生成趋势图")
            return None
        
        # 获取今日TOP N板块
        today = datetime.now().strftime('%Y-%m-%d')
        today_data = df[df['date'] == today]
        
        if today_data.empty:
            # 如果没有今天数据，使用最新一天
            latest_date = df['date'].max()
            today_data = df[df['date'] == latest_date]
            self.logger.info(f"使用最新日期数据: {latest_date}")
        
        # 按净流入排序取TOP N
        if 'main_inflow' in today_data.columns:
            top_sectors = today_data.nlargest(top_n, 'main_inflow')['sector_name'].tolist()
        elif 'super_large_inflow' in today_data.columns:
            top_sectors = today_data.nlargest(top_n, 'super_large_inflow')['sector_name'].tolist()
        else:
            # 尝试找到净流入列
            inflow_cols = [c for c in today_data.columns if 'inflow' in c or '净流入' in c]
            if inflow_cols:
                top_sectors = today_data.nlargest(top_n, inflow_cols[0])['sector_name'].tolist()
            else:
                self.logger.warning("未找到净流入列")
                return None
        
        # 过滤这些板块的历史数据
        sector_data = df[df['sector_name'].isin(top_sectors)].copy()
        
        # 转换日期
        sector_data['date'] = pd.to_datetime(sector_data['date'])
        
        # 获取净流入列
        inflow_col = self._get_inflow_column(sector_data)
        if not inflow_col:
            self.logger.error("无法确定净流入列")
            return None
        
        # 转换为亿元
        sector_data['inflow_yi'] = sector_data[inflow_col] / 1e8
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        colors = plt.cm.tab10(range(len(top_sectors)))
        
        for i, sector in enumerate(top_sectors):
            sector_df = sector_data[sector_data['sector_name'] == sector]
            sector_df = sector_df.sort_values('date')
            
            ax.plot(sector_df['date'], sector_df['inflow_yi'], 
                   marker='o', linewidth=2, markersize=4,
                   label=sector, color=colors[i])
        
        # 设置图表样式
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Net Inflow (Billion CNY)', fontsize=12)
        ax.set_title(f'TOP {top_n} Sectors - Capital Flow Trend (Last {days} Days)', 
                    fontsize=14, fontweight='bold')
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.grid(True, alpha=0.3)
        
        # 格式化x轴日期
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, days//7)))
        plt.xticks(rotation=45)
        
        # 添加零线
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        
        # 保存图表
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_file = self.charts_path / f"top_sectors_trend_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        self.logger.info(f"趋势图已保存: {chart_file}")
        return str(chart_file)
    
    def generate_sector_comparison(self, sectors: List[str], days: int = 7) -> str:
        """
        生成指定板块对比图
        
        Args:
            sectors: 板块名称列表
            days: 最近N天
            
        Returns:
            str: 图表文件路径
        """
        df = self.load_historical_data(days=days)
        
        if df.empty:
            return None
        
        sector_data = df[df['sector_name'].isin(sectors)].copy()
        sector_data['date'] = pd.to_datetime(sector_data['date'])
        
        inflow_col = self._get_inflow_column(sector_data)
        if not inflow_col:
            return None
        
        sector_data['inflow_yi'] = sector_data[inflow_col] / 1e8
        
        # 创建子图
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))
        
        # 图1: 资金流向趋势
        ax1 = axes[0]
        for sector in sectors:
            sector_df = sector_data[sector_data['sector_name'] == sector]
            sector_df = sector_df.sort_values('date')
            ax1.plot(sector_df['date'], sector_df['inflow_yi'], 
                    marker='o', label=sector, linewidth=2)
        
        ax1.set_ylabel('Net Inflow (Billion)', fontsize=11)
        ax1.set_title('Capital Flow Trend Comparison', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # 图2: 涨跌幅对比
        ax2 = axes[1]
        if 'change_pct' in sector_data.columns:
            for sector in sectors:
                sector_df = sector_data[sector_data['sector_name'] == sector]
                sector_df = sector_df.sort_values('date')
                ax2.plot(sector_df['date'], sector_df['change_pct'], 
                        marker='s', label=sector, linewidth=2)
            
            ax2.set_ylabel('Change %', fontsize=11)
            ax2.set_title('Price Change Comparison', fontsize=12, fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # 格式化x轴
        for ax in axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_file = self.charts_path / f"sector_comparison_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_file)
    
    def generate_market_heatmap(self, days: int = 5) -> str:
        """
        生成板块资金流向热力图
        
        Args:
            days: 最近N天
            
        Returns:
            str: 图表文件路径
        """
        df = self.load_historical_data(days=days)
        
        if df.empty or len(df['date'].unique()) < 2:
            self.logger.warning("数据不足，无法生成热力图")
            return None
        
        # 获取每日TOP10板块
        inflow_col = self._get_inflow_column(df)
        if not inflow_col:
            return None
        
        df['inflow_yi'] = df[inflow_col] / 1e8
        
        # 取每天TOP15板块
        top_sectors_by_day = []
        for date in sorted(df['date'].unique())[-days:]:
            day_data = df[df['date'] == date]
            top_15 = day_data.nlargest(15, 'inflow_yi')['sector_name'].tolist()
            top_sectors_by_day.extend(top_15)
        
        # 获取出现频率最高的20个板块
        from collections import Counter
        sector_freq = Counter(top_sectors_by_day)
        frequent_sectors = [s for s, _ in sector_freq.most_common(20)]
        
        # 构建透视表
        pivot_data = []
        for date in sorted(df['date'].unique())[-days:]:
            day_data = df[df['date'] == date]
            for sector in frequent_sectors:
                sector_row = day_data[day_data['sector_name'] == sector]
                if not sector_row.empty:
                    pivot_data.append({
                        'date': date,
                        'sector': sector,
                        'inflow': sector_row['inflow_yi'].values[0]
                    })
                else:
                    pivot_data.append({
                        'date': date,
                        'sector': sector,
                        'inflow': 0
                    })
        
        pivot_df = pd.DataFrame(pivot_data)
        pivot_table = pivot_df.pivot(index='sector', columns='date', values='inflow')
        
        # 创建热力图
        fig, ax = plt.subplots(figsize=(10, 12))
        
        im = ax.imshow(pivot_table.values, cmap='RdYlGn', aspect='auto', vmin=-10, vmax=10)
        
        # 设置标签
        ax.set_xticks(range(len(pivot_table.columns)))
        ax.set_xticklabels([d[-5:] for d in pivot_table.columns], rotation=45)
        ax.set_yticks(range(len(pivot_table.index)))
        ax.set_yticklabels(pivot_table.index, fontsize=9)
        
        # 添加数值
        for i in range(len(pivot_table.index)):
            for j in range(len(pivot_table.columns)):
                val = pivot_table.values[i, j]
                text_color = 'white' if abs(val) > 5 else 'black'
                ax.text(j, i, f'{val:.1f}', ha='center', va='center', 
                       color=text_color, fontsize=8)
        
        ax.set_title('Sector Capital Flow Heatmap (Billion CNY)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Net Inflow (Billion)', rotation=270, labelpad=20)
        
        plt.tight_layout()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chart_file = self.charts_path / f"market_heatmap_{timestamp}.png"
        plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return str(chart_file)
    
    def _get_inflow_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        获取净流入列名
        
        Args:
            df: DataFrame
            
        Returns:
            Optional[str]: 列名
        """
        candidates = ['main_inflow', 'super_large_inflow', '今日主力净流入-净额', '今日超大单净流入-净额']
        
        for col in candidates:
            if col in df.columns:
                return col
        
        # 尝试模糊匹配
        for col in df.columns:
            if 'inflow' in col.lower() or '净流入' in col:
                return col
        
        return None
    
    def generate_sector_history_chart(self, sector_name: str, df: pd.DataFrame = None, days: int = 30) -> str:
        """
        生成单个板块的长期趋势图

        Args:
            sector_name: 板块名称
            df: 可选，历史数据DataFrame。如未提供，则从本地加载
            days: 显示最近多少天的数据

        Returns:
            str: 生成的图表文件路径
        """
        try:
            # 如果未提供数据，从本地加载
            if df is None or df.empty:
                df = self.load_historical_data(days=days)

            if df.empty:
                self.logger.warning("无历史数据，无法生成趋势图")
                return None

            # 过滤指定板块的数据
            if 'sector_name' not in df.columns:
                self.logger.error("数据中缺少sector_name列")
                return None

            sector_df = df[df['sector_name'] == sector_name].copy()

            if sector_df.empty:
                self.logger.warning(f"未找到板块 '{sector_name}' 的历史数据")
                return None

            # 确保日期列存在并转换
            if 'date' in sector_df.columns:
                sector_df['date'] = pd.to_datetime(sector_df['date'])
                sector_df = sector_df.sort_values('date')

            # 限制显示天数
            if len(sector_df) > days:
                sector_df = sector_df.tail(days)

            # 获取净流入列
            inflow_col = self._get_inflow_column(sector_df)
            if not inflow_col:
                self.logger.error("无法确定净流入列")
                return None

            # 转换为亿元
            sector_df['inflow_yi'] = sector_df[inflow_col] / 1e8

            # 创建图表
            fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [2, 1]})

            # 图1: 主力资金流向趋势
            ax1 = axes[0]
            colors = ['green' if x >= 0 else 'red' for x in sector_df['inflow_yi']]
            ax1.bar(sector_df['date'], sector_df['inflow_yi'], color=colors, alpha=0.7, width=0.8)
            ax1.plot(sector_df['date'], sector_df['inflow_yi'], color='black', linewidth=1.5, marker='o', markersize=3)

            # 添加移动平均线
            if len(sector_df) >= 5:
                sector_df['ma5'] = sector_df['inflow_yi'].rolling(window=5).mean()
                ax1.plot(sector_df['date'], sector_df['ma5'], color='blue', linewidth=2, label='MA5', linestyle='--')

            ax1.set_ylabel('Net Inflow (Billion CNY)', fontsize=11)
            ax1.set_title(f'{sector_name} - Capital Flow Trend (Last {len(sector_df)} Days)', fontsize=14, fontweight='bold')
            ax1.legend()
            ax1.grid(True, alpha=0.3, axis='y')
            ax1.axhline(y=0, color='gray', linestyle='-', alpha=0.5)

            # 图2: 涨跌幅
            ax2 = axes[1]
            if 'change_pct' in sector_df.columns:
                colors_pct = ['green' if x >= 0 else 'red' for x in sector_df['change_pct']]
                ax2.bar(sector_df['date'], sector_df['change_pct'], color=colors_pct, alpha=0.7, width=0.8)
                ax2.set_ylabel('Change %', fontsize=11)
                ax2.set_title('Daily Price Change', fontsize=12)
                ax2.grid(True, alpha=0.3, axis='y')
                ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
            else:
                ax2.text(0.5, 0.5, 'No change_pct data available', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_xticks([])
                ax2.set_yticks([])

            # 格式化x轴日期
            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(sector_df) // 8)))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

            # 添加统计信息文本框
            if len(sector_df) > 0:
                avg_inflow = sector_df['inflow_yi'].mean()
                total_inflow = sector_df['inflow_yi'].sum()
                positive_days = (sector_df['inflow_yi'] > 0).sum()

                stats_text = f'Avg: {avg_inflow:.2f}B | Total: {total_inflow:.2f}B | Pos Days: {positive_days}/{len(sector_df)}'
                fig.text(0.5, 0.02, stats_text, ha='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

            plt.tight_layout(rect=[0, 0.05, 1, 1])

            # 保存图表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = sector_name.replace('/', '_').replace('\\', '_')
            chart_file = self.charts_path / f"sector_history_{safe_name}_{timestamp}.png"
            plt.savefig(chart_file, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            self.logger.info(f"板块历史趋势图已保存: {chart_file}")
            return str(chart_file)

        except Exception as e:
            self.logger.error(f"生成板块历史趋势图失败: {str(e)}")
            return None

    def cleanup_old_charts(self, keep_days: int = 7):
        """
        清理旧图表文件

        Args:
            keep_days: 保留最近N天的图表
        """
        cutoff = datetime.now() - timedelta(days=keep_days)

        for chart_file in self.charts_path.glob('*.png'):
            try:
                # 从文件名提取日期
                file_stat = chart_file.stat()
                file_time = datetime.fromtimestamp(file_stat.st_mtime)

                if file_time < cutoff:
                    chart_file.unlink()
                    self.logger.debug(f"删除旧图表: {chart_file}")
            except Exception as e:
                self.logger.warning(f"清理图表失败 {chart_file}: {e}")

        self.logger.info(f"图表清理完成，保留最近 {keep_days} 天")
