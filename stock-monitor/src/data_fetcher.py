"""数据获取模块 - 使用akshare获取板块资金流"""
import logging
import time
import akshare as ak
import pandas as pd
from typing import Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataFetcher:
    """数据获取器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._last_request_time = 0
        self._min_request_interval = 0.5  # akshare接口限速，最小请求间隔0.5秒
    
    def get_sector_flow(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取板块资金流排名
        
        Args:
            trade_date: 交易日期，格式为 YYYYMMDD，None表示获取最新数据
            
        Returns:
            pd.DataFrame: 板块资金流数据
            
        Raises:
            ConnectionError: 网络错误
            ValueError: API返回空数据
        """
        try:
            self.logger.info(f"正在获取板块资金流数据...")
            
            # 使用akshare获取板块资金流排名
            # indicator参数: "今日排行", "5日排行", "10日排行", "20日排行"
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
            
            if df is None or df.empty:
                raise ValueError("API返回空数据")
            
            # 标准化列名
            df = self._normalize_columns(df)
            
            # 添加日期字段
            if trade_date:
                df['trade_date'] = trade_date
            
            self.logger.info(f"成功获取 {len(df)} 条板块数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取数据失败: {str(e)}")
            if "网络" in str(e) or "Connection" in str(e):
                raise ConnectionError(f"网络错误: {str(e)}")
            raise
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            '名称': 'sector_name',
            '今日涨跌幅': 'change_pct',
            '主力净流入-净额': 'main_inflow',
            '主力净流入-净占比': 'main_inflow_pct',
            '超大单净流入-净额': 'super_large_inflow',
            '超大单净流入-净占比': 'super_large_inflow_pct',
            '大单净流入-净额': 'large_inflow',
            '大单净流入-净占比': 'large_inflow_pct',
            '中单净流入-净额': 'medium_inflow',
            '中单净流入-净占比': 'medium_inflow_pct',
            '小单净流入-净额': 'small_inflow',
            '小单净流入-净占比': 'small_inflow_pct',
            # akshare实际返回的列名（带"今日"前缀）
            '今日主力净流入-净额': 'main_inflow',
            '今日主力净流入-净占比': 'main_inflow_pct',
            '今日超大单净流入-净额': 'super_large_inflow',
            '今日超大单净流入-净占比': 'super_large_inflow_pct',
            '今日大单净流入-净额': 'large_inflow',
            '今日大单净流入-净占比': 'large_inflow_pct',
            '今日中单净流入-净额': 'medium_inflow',
            '今日中单净流入-净占比': 'medium_inflow_pct',
            '今日小单净流入-净额': 'small_inflow',
            '今日小单净流入-净占比': 'small_inflow_pct',
        }

        # 重命名存在的列
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})

        return df

    def _rate_limit(self):
        """请求频率限制，确保不会过快调用API"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def get_sector_flow_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        获取单个板块的历史资金流数据

        Args:
            symbol: 板块名称（如"半导体"、"白酒"等）
            days: 获取最近多少天的数据（akshare接口会返回可用历史数据）

        Returns:
            pd.DataFrame: 包含日期、净流入、涨跌幅的DataFrame
                列名: date, sector_name, main_inflow, change_pct
        """
        try:
            self._rate_limit()
            self.logger.info(f"正在获取板块 '{symbol}' 的历史资金流数据...")

            # 使用akshare获取板块历史资金流
            df = ak.stock_sector_fund_flow_hist(symbol=symbol)

            if df is None or df.empty:
                self.logger.warning(f"板块 '{symbol}' 无历史数据")
                return pd.DataFrame()

            # 标准化列名（历史数据接口返回的列名与当日数据略有不同）
            column_mapping = {
                '日期': 'date',
                '名称': 'sector_name',
                '主力净流入-净额': 'main_inflow',
                '主力净流入-净占比': 'main_inflow_pct',
                '超大单净流入-净额': 'super_large_inflow',
                '超大单净流入-净占比': 'super_large_inflow_pct',
                '大单净流入-净额': 'large_inflow',
                '大单净流入-净占比': 'large_inflow_pct',
                '中单净流入-净额': 'medium_inflow',
                '中单净流入-净占比': 'medium_inflow_pct',
                '小单净流入-净额': 'small_inflow',
                '小单净流入-净占比': 'small_inflow_pct',
                '涨跌幅': 'change_pct',
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})

            # 确保日期格式统一
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')

            # 添加板块名称（如果接口返回的为空）
            if 'sector_name' not in df.columns or df['sector_name'].isna().all():
                df['sector_name'] = symbol

            # 按日期降序排列，取最近days天
            df = df.sort_values('date', ascending=False).head(days).reset_index(drop=True)

            self.logger.info(f"成功获取 '{symbol}' 历史数据 {len(df)} 条")
            return df

        except Exception as e:
            self.logger.error(f"获取板块 '{symbol}' 历史数据失败: {str(e)}")
            return pd.DataFrame()

    def get_all_sectors_historical(self, sectors: List[str], days: int = 30) -> pd.DataFrame:
        """
        批量获取多个板块的历史数据并合并

        Args:
            sectors: 板块名称列表
            days: 每个板块获取最近多少天的数据

        Returns:
            pd.DataFrame: 合并后的历史数据，包含所有板块
        """
        all_data = []

        for i, sector in enumerate(sectors):
            df = self.get_sector_flow_historical(sector, days=days)
            if not df.empty:
                all_data.append(df)

            # 添加短暂延迟，避免触发接口限速
            if i < len(sectors) - 1:
                time.sleep(0.3)

        if not all_data:
            self.logger.warning("未获取到任何板块的历史数据")
            return pd.DataFrame()

        combined = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"批量获取完成，共 {len(sectors)} 个板块，{len(combined)} 条记录")
        return combined

    def backfill_historical_data(self, sectors: List[str], end_date: str, days: int = 30) -> pd.DataFrame:
        """
        回填历史数据到指定日期

        Args:
            sectors: 板块名称列表
            end_date: 结束日期，格式 YYYY-MM-DD
            days: 从结束日期往前回溯多少天

        Returns:
            pd.DataFrame: 过滤后的历史数据（在指定日期范围内）
        """
        try:
            # 获取所有板块的历史数据
            df = self.get_all_sectors_historical(sectors, days=days)

            if df.empty:
                return df

            # 解析日期
            end_dt = datetime.strptime(end_date.replace('-', ''), '%Y%m%d')
            start_dt = end_dt - timedelta(days=days)

            # 过滤日期范围
            df['date'] = pd.to_datetime(df['date'])
            mask = (df['date'] >= start_dt) & (df['date'] <= end_dt)
            filtered_df = df.loc[mask].copy()

            # 转换回字符串格式
            filtered_df['date'] = filtered_df['date'].dt.strftime('%Y-%m-%d')

            self.logger.info(f"回填数据完成: {start_dt.date()} 至 {end_dt.date()}, 共 {len(filtered_df)} 条")
            return filtered_df

        except Exception as e:
            self.logger.error(f"回填历史数据失败: {str(e)}")
            return pd.DataFrame()
