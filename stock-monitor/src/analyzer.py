"""分析器模块 - 板块排名和轮动检测"""
import logging
import pandas as pd
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SectorAnalyzer:
    """板块分析器类"""
    
    def __init__(self, data_path: str = "/app/data"):
        self.data_path = data_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 确保数据目录存在
        os.makedirs(data_path, exist_ok=True)
    
    def rank_by_inflow(self, df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        按主力净流入排序
        
        Args:
            df: 板块资金流数据
            top_n: 返回前N名
            
        Returns:
            pd.DataFrame: 排序后的数据
        """
        if df is None or df.empty:
            self.logger.warning("输入数据为空")
            return pd.DataFrame()
        
        # 按主力净流入排序（从高到低）
        if 'main_inflow' in df.columns:
            df_sorted = df.sort_values('main_inflow', ascending=False).reset_index(drop=True)
        else:
            # 如果没有main_inflow列，尝试找相关的净流入列
            inflow_col = None
            for col in df.columns:
                if '净流入' in col or 'inflow' in col:
                    inflow_col = col
                    break
            
            if inflow_col:
                df_sorted = df.sort_values(inflow_col, ascending=False).reset_index(drop=True)
            else:
                df_sorted = df.copy()
        
        # 添加排名
        df_sorted['rank'] = range(1, len(df_sorted) + 1)
        
        return df_sorted.head(top_n)
    
    def detect_rotation(self, today_df: pd.DataFrame, yesterday_df: pd.DataFrame) -> List[Dict]:
        """
        检测新进入TOP10的板块（轮动信号）
        
        Args:
            today_df: 今日排名数据
            yesterday_df: 昨日排名数据
            
        Returns:
            List[Dict]: 轮动信号列表，每项包含板块名和昨日排名
        """
        rotation_signals = []
        
        if today_df is None or today_df.empty:
            self.logger.warning("今日数据为空，无法检测轮动")
            return rotation_signals
        
        if yesterday_df is None or yesterday_df.empty:
            self.logger.warning("昨日数据为空，无法检测轮动")
            return rotation_signals
        
        # 获取今日TOP10板块名
        today_sectors = set()
        if 'sector_name' in today_df.columns:
            today_sectors = set(today_df['sector_name'].head(10))
        elif 'name' in today_df.columns:
            today_sectors = set(today_df['name'].head(10))
        
        # 获取昨日TOP10板块名
        yesterday_sectors = set()
        yesterday_ranks = {}
        
        if 'sector_name' in yesterday_df.columns:
            for idx, row in yesterday_df.iterrows():
                sector = row['sector_name']
                rank = row.get('rank', idx + 1)
                yesterday_ranks[sector] = rank
                if idx < 10:
                    yesterday_sectors.add(sector)
        elif 'name' in yesterday_df.columns:
            for idx, row in yesterday_df.iterrows():
                sector = row['name']
                rank = row.get('rank', idx + 1)
                yesterday_ranks[sector] = rank
                if idx < 10:
                    yesterday_sectors.add(sector)
        
        # 找出新进入TOP10的板块
        new_sectors = today_sectors - yesterday_sectors
        
        for sector in new_sectors:
            yesterday_rank = yesterday_ranks.get(sector, ">10")
            rotation_signals.append({
                'sector_name': sector,
                'yesterday_rank': yesterday_rank,
                'signal_type': '新进入TOP10'
            })
        
        self.logger.info(f"检测到 {len(rotation_signals)} 个轮动信号")
        return rotation_signals
    
    def save_snapshot(self, df: pd.DataFrame, date_str: str) -> str:
        """
        保存当日数据到CSV
        
        Args:
            df: 板块数据
            date_str: 日期字符串 (YYYY-MM-DD 或 YYYYMMDD)
            
        Returns:
            str: 保存的文件路径
        """
        # 标准化日期格式
        date_str = date_str.replace('-', '')
        
        file_path = os.path.join(self.data_path, f"sector_flow_{date_str}.csv")
        
        try:
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.logger.info(f"数据已保存到: {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"保存数据失败: {str(e)}")
            raise
    
    def load_snapshot(self, date_str: str) -> Optional[pd.DataFrame]:
        """
        读取某日数据
        
        Args:
            date_str: 日期字符串 (YYYY-MM-DD 或 YYYYMMDD)
            
        Returns:
            Optional[pd.DataFrame]: 板块数据，不存在返回None
        """
        # 标准化日期格式
        date_str = date_str.replace('-', '')
        
        file_path = os.path.join(self.data_path, f"sector_flow_{date_str}.csv")
        
        if not os.path.exists(file_path):
            self.logger.warning(f"数据文件不存在: {file_path}")
            return None
        
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            self.logger.info(f"已加载数据: {file_path}, 共 {len(df)} 条")
            return df
        except Exception as e:
            self.logger.error(f"读取数据失败: {str(e)}")
            return None
    
    def get_last_trading_date(self, date_str: str) -> str:
        """
        获取上一个交易日（简单处理，跳过周末）

        Args:
            date_str: 当前日期 (YYYY-MM-DD)

        Returns:
            str: 上一个交易日 (YYYY-MM-DD)
        """
        date = datetime.strptime(date_str.replace('-', ''), '%Y%m%d')

        # 简单处理：回退1-3天，跳过周末
        for i in range(1, 10):
            prev_date = date - timedelta(days=i)
            # 跳过周六(5)和周日(6)
            if prev_date.weekday() < 5:
                return prev_date.strftime('%Y-%m-%d')

        # 默认回退1天
        return (date - timedelta(days=1)).strftime('%Y-%m-%d')

    def load_historical_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        加载日期范围内的所有历史数据

        Args:
            start_date: 开始日期，格式 YYYY-MM-DD
            end_date: 结束日期，格式 YYYY-MM-DD

        Returns:
            pd.DataFrame: 合并后的历史数据
        """
        try:
            start_dt = datetime.strptime(start_date.replace('-', ''), '%Y%m%d')
            end_dt = datetime.strptime(end_date.replace('-', ''), '%Y%m%d')

            all_data = []
            current_dt = start_dt

            while current_dt <= end_dt:
                date_str = current_dt.strftime('%Y-%m-%d')
                df = self.load_snapshot(date_str)

                if df is not None and not df.empty:
                    # 确保有date列
                    if 'date' not in df.columns:
                        df['date'] = date_str
                    all_data.append(df)

                current_dt += timedelta(days=1)

            if not all_data:
                self.logger.warning(f"未找到 {start_date} 至 {end_date} 的历史数据")
                return pd.DataFrame()

            combined = pd.concat(all_data, ignore_index=True)
            self.logger.info(f"加载历史数据范围: {start_date} 至 {end_date}, 共 {len(combined)} 条")
            return combined

        except Exception as e:
            self.logger.error(f"加载历史数据范围失败: {str(e)}")
            return pd.DataFrame()

    def calculate_trend_strength(self, df: pd.DataFrame, sector_name: str, days: int = 5) -> Dict:
        """
        计算板块近期趋势强度

        Args:
            df: 历史数据DataFrame，包含date和main_inflow列
            sector_name: 板块名称
            days: 计算最近多少天的趋势

        Returns:
            Dict: 趋势分析结果
                - trend_score: 趋势得分 (-100 到 100)
                - trend_direction: 趋势方向 ('up', 'down', 'neutral')
                - avg_inflow: 平均净流入
                - consistency: 一致性（净流入为正的天数比例）
                - momentum: 动量（近期相对于前期的变化）
        """
        try:
            # 过滤板块数据
            if 'sector_name' not in df.columns:
                return {
                    'trend_score': 0,
                    'trend_direction': 'neutral',
                    'avg_inflow': 0,
                    'consistency': 0,
                    'momentum': 0,
                    'error': '数据中缺少sector_name列'
                }

            sector_df = df[df['sector_name'] == sector_name].copy()

            if sector_df.empty:
                return {
                    'trend_score': 0,
                    'trend_direction': 'neutral',
                    'avg_inflow': 0,
                    'consistency': 0,
                    'momentum': 0,
                    'error': f'未找到板块 {sector_name} 的数据'
                }

            # 确保日期列存在并排序
            if 'date' in sector_df.columns:
                sector_df['date'] = pd.to_datetime(sector_df['date'])
                sector_df = sector_df.sort_values('date', ascending=False)

            # 获取最近N天的数据
            recent_data = sector_df.head(days)

            if recent_data.empty or len(recent_data) < 2:
                return {
                    'trend_score': 0,
                    'trend_direction': 'neutral',
                    'avg_inflow': 0,
                    'consistency': 0,
                    'momentum': 0,
                    'error': '数据不足，无法计算趋势'
                }

            # 获取净流入列
            inflow_col = None
            for col in ['main_inflow', 'super_large_inflow', '今日主力净流入-净额']:
                if col in recent_data.columns:
                    inflow_col = col
                    break

            if inflow_col is None:
                return {
                    'trend_score': 0,
                    'trend_direction': 'neutral',
                    'avg_inflow': 0,
                    'consistency': 0,
                    'momentum': 0,
                    'error': '未找到净流入列'
                }

            inflows = recent_data[inflow_col].values
            
            # 转换为Python列表，避免numpy数组比较问题
            inflows_list = [float(x) for x in inflows if pd.notna(x)]
            
            if not inflows_list:
                return {
                    'trend_score': 0,
                    'trend_direction': 'neutral',
                    'avg_inflow': 0,
                    'consistency': 0,
                    'momentum': 0,
                    'error': '无有效数据'
                }

            # 计算平均净流入
            avg_inflow = sum(inflows_list) / len(inflows_list)

            # 计算一致性（净流入为正的天数比例）
            positive_days = sum(1 for x in inflows_list if x > 0)
            consistency = positive_days / len(inflows_list) if inflows_list else 0

            # 计算动量（后一半vs前一半）
            mid = len(inflows_list) // 2
            if mid > 0:
                first_half = sum(inflows_list[:mid]) / mid
                second_half = sum(inflows_list[mid:]) / (len(inflows_list) - mid)
                momentum = second_half - first_half if first_half != 0 else 0
            else:
                momentum = 0

            # 计算趋势得分 (-100 到 100)
            # 综合因素：平均值、一致性、动量
            avg_norm = max(-1, min(1, avg_inflow / 1e8))  # 归一化到 -1 ~ 1
            consistency_score = (consistency - 0.5) * 2  # -1 ~ 1
            momentum_norm = max(-1, min(1, momentum / 1e8))  # 归一化

            trend_score = (avg_norm * 40 + consistency_score * 30 + momentum_norm * 30)
            trend_score = max(-100, min(100, trend_score))

            # 确定趋势方向
            if trend_score > 20:
                trend_direction = 'up'
            elif trend_score < -20:
                trend_direction = 'down'
            else:
                trend_direction = 'neutral'

            return {
                'trend_score': round(trend_score, 2),
                'trend_direction': trend_direction,
                'avg_inflow': round(avg_inflow, 2),
                'consistency': round(consistency, 2),
                'momentum': round(momentum, 2),
                'data_points': len(inflows)
            }

        except Exception as e:
            self.logger.error(f"计算趋势强度失败: {str(e)}")
            return {
                'trend_score': 0,
                'trend_direction': 'neutral',
                'avg_inflow': 0,
                'consistency': 0,
                'momentum': 0,
                'error': str(e)
            }
