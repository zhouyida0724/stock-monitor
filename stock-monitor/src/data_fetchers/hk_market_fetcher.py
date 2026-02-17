"""港股数据获取器 - 基于AKShare获取恒生行业指数"""
import logging
import time
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

from .base import BaseDataFetcher, MarketType

try:
    import akshare as ak
except ImportError:
    ak = None

try:
    import yfinance as yf
except ImportError:
    yf = None


# 恒生行业指数代码映射（部分常用指数）
# 注意：实际代码可能需要根据AKShare最新接口调整
HSI_SECTOR_CODES = {
    "能源": "HSCEI",
    "原材料": "HSMCI",
    "工业": "HSII", 
    "消费": "HSCDI",
    "医药": "HSHCI",
    "金融": "HSFI",
    "地产": "HSPI",
    "科技": "HSTI",
    "公用": "HSUI",
    "电讯": "HSTLI",
}

# 港股主要ETF作为板块代理（使用yfinance）
HK_SECTOR_ETFS = {
    "恒生科技": "3033.HK",      # 恒生科技指数ETF
    "恒生金融": "2828.HK",      # 恒生H股金融指数
    "恒生地产": "2801.HK",      # 恒生地产指数
    "恒生消费": "3037.HK",      # 恒生消费指数
    "恒生医药": "2838.HK",      # 恒生医药指数
}


class HKMarketDataFetcher(BaseDataFetcher):
    """港股板块数据获取器
    
    使用AKShare获取恒生行业指数，或使用yfinance获取港股ETF数据
    """
    
    def __init__(self, use_etfs: bool = True):
        """
        Args:
            use_etfs: 是否使用ETF作为板块代理（默认True，更稳定）
        """
        super().__init__()
        self.market_type = MarketType.HK
        self.use_etfs = use_etfs
        self._last_request_time = 0
        self._min_request_interval = 0.5
        
        if use_etfs and yf is None:
            raise ImportError("使用ETF模式需要yfinance: pip install yfinance")
        if not use_etfs and ak is None:
            raise ImportError("使用AKShare模式需要akshare: pip install akshare")
    
    def _rate_limit(self):
        """请求频率限制"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取港股板块数据
        
        优先使用ETF模式（更稳定），
        或使用AKShare获取恒生行业指数
        
        Args:
            trade_date: 交易日期，格式 YYYYMMDD
            
        Returns:
            pd.DataFrame: 板块数据
        """
        if self.use_etfs:
            return self._get_etf_data(trade_date)
        else:
            return self._get_hs_index_data(trade_date)
    
    def _get_etf_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """使用港股ETF获取板块数据"""
        try:
            self.logger.info(f"正在获取港股ETF板块数据...")
            
            data_list = []
            
            for sector_name, symbol in HK_SECTOR_ETFS.items():
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d")
                    
                    if hist.empty or len(hist) < 1:
                        self.logger.warning(f"无法获取 {symbol} 数据")
                        continue
                    
                    # 获取最新数据
                    latest = hist.iloc[-1]
                    prev_close = hist.iloc[-2]['Close'] if len(hist) >= 2 else latest['Open']
                    
                    # 计算涨跌幅
                    change_pct = ((latest['Close'] - prev_close) / prev_close) * 100
                    
                    # 获取成交量
                    volume = int(latest['Volume'])
                    
                    # 估算资金流向
                    price_change = latest['Close'] - prev_close
                    estimated_inflow = price_change * volume
                    
                    data_list.append({
                        'sector_name': sector_name,
                        'symbol': symbol,
                        'change_pct': round(change_pct, 2),
                        'main_inflow': estimated_inflow,
                        'volume': volume,
                        'close_price': round(latest['Close'], 2),
                        'prev_close': round(prev_close, 2),
                    })
                    
                except Exception as e:
                    self.logger.warning(f"获取 {symbol} 数据失败: {e}")
                    continue
            
            if not data_list:
                raise ValueError("无法获取任何港股ETF数据")
            
            df = pd.DataFrame(data_list)
            
            # 按估算资金流向排序
            df = df.sort_values('main_inflow', ascending=False).reset_index(drop=True)
            
            # 添加日期
            df['trade_date'] = trade_date or datetime.now().strftime('%Y%m%d')
            
            self.logger.info(f"成功获取 {len(df)} 个港股板块数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取港股ETF数据失败: {str(e)}")
            raise
    
    def _get_hs_index_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """使用AKShare获取恒生指数数据"""
        try:
            self.logger.info(f"正在获取恒生行业指数数据...")
            
            # 使用AKShare获取港股行情
            # 尝试获取恒生指数成分股作为代理
            self._rate_limit()
            
            # 获取港股实时行情
            df = ak.stock_hk_ggt_components_em()
            
            if df is None or df.empty:
                raise ValueError("API返回空数据")
            
            # 标准化列名
            df = self._normalize_columns(df)
            
            # 按行业分组（简化处理：使用名称关键词分类）
            df = self._classify_sectors(df)
            
            # 添加日期
            if trade_date:
                df['trade_date'] = trade_date
            
            self.logger.info(f"成功获取 {len(df)} 条港股行业数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取恒生指数数据失败: {str(e)}")
            # 如果失败，尝试ETF模式
            self.logger.info("尝试使用ETF模式获取数据...")
            return self._get_etf_data(trade_date)
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化列名"""
        column_mapping = {
            '名称': 'sector_name',
            '最新价': 'close_price',
            '涨跌幅': 'change_pct',
            '涨跌额': 'change_amount',
            '成交量': 'volume',
            '成交额': 'turnover',
            '买入': 'buy_amount',
            '卖出': 'sell_amount',
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})

        return df
    
    def _classify_sectors(self, df: pd.DataFrame) -> pd.DataFrame:
        """根据股票名称分类到行业板块"""
        # 简化分类规则
        sector_keywords = {
            '金融': ['银行', '保险', '证券', '金融'],
            '地产': ['地产', '物业', '置业'],
            '科技': ['科技', '软件', '互联网', '电子'],
            '医药': ['医药', '生物', '医疗', '药业'],
            '消费': ['食品', '饮料', '零售', '消费'],
            '能源': ['石油', '煤炭', '电力', '能源'],
            '电讯': ['电讯', '通信', '移动'],
        }
        
        def get_sector(name):
            for sector, keywords in sector_keywords.items():
                if any(kw in name for kw in keywords):
                    return sector
            return '其他'
        
        df['sector_name'] = df.get('sector_name', df.get('名称', '')).apply(get_sector)
        
        # 按板块汇总
        agg_df = df.groupby('sector_name').agg({
            'change_pct': 'mean',
            'volume': 'sum',
            'turnover': 'sum' if 'turnover' in df.columns else 'volume',
        }).reset_index()
        
        # 估算资金流向（使用成交额 * 涨跌幅方向）
        turnover_col = 'turnover' if 'turnover' in agg_df.columns else 'volume'
        agg_df['main_inflow'] = agg_df[turnover_col] * agg_df['change_pct'] / 100
        
        return agg_df
    
    def get_sector_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取单个板块的历史数据
        
        Args:
            symbol: 板块名称或ETF代码
            days: 获取最近多少天的数据
            
        Returns:
            pd.DataFrame: 历史数据
        """
        if self.use_etfs or symbol in HK_SECTOR_ETFS or symbol.endswith('.HK'):
            return self._get_etf_historical(symbol, days)
        else:
            return self._get_hs_index_historical(symbol, days)
    
    def _get_etf_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取ETF历史数据"""
        try:
            # 确定板块名称和代码
            if symbol in HK_SECTOR_ETFS:
                sector_name = symbol
                etf_symbol = HK_SECTOR_ETFS[symbol]
            elif symbol in HK_SECTOR_ETFS.values():
                etf_symbol = symbol
                sector_name = [k for k, v in HK_SECTOR_ETFS.items() if v == symbol][0]
            else:
                etf_symbol = symbol
                sector_name = symbol
            
            self.logger.info(f"正在获取 {etf_symbol} ({sector_name}) 的历史数据...")
            
            ticker = yf.Ticker(etf_symbol)
            hist = ticker.history(period=f"{days + 5}d")
            
            if hist.empty:
                return pd.DataFrame()
            
            hist = hist.reset_index()
            hist['Date'] = pd.to_datetime(hist['Date']).dt.strftime('%Y-%m-%d')
            
            data_list = []
            for i in range(1, len(hist)):
                row = hist.iloc[i]
                prev_row = hist.iloc[i-1]
                
                change_pct = ((row['Close'] - prev_row['Close']) / prev_row['Close']) * 100
                price_change = row['Close'] - prev_row['Close']
                estimated_inflow = price_change * row['Volume']
                
                data_list.append({
                    'date': row['Date'],
                    'sector_name': sector_name,
                    'symbol': etf_symbol,
                    'change_pct': round(change_pct, 2),
                    'main_inflow': estimated_inflow,
                    'close_price': round(row['Close'], 2),
                    'volume': int(row['Volume']),
                })
            
            df = pd.DataFrame(data_list)
            df = df.sort_values('date', ascending=False).head(days).reset_index(drop=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"获取ETF历史数据失败: {e}")
            return pd.DataFrame()
    
    def _get_hs_index_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取恒生行业指数历史数据"""
        try:
            # 使用AKShare获取历史数据
            # 这里简化处理，使用恒生指数作为代理
            self._rate_limit()
            
            # 获取恒生指数历史数据
            df = ak.index_hk_hist(symbol="HSI", period="daily")
            
            if df.empty:
                return pd.DataFrame()
            
            # 标准化列名
            df = df.rename(columns={
                '日期': 'date',
                '收盘': 'close_price',
                '涨跌幅': 'change_pct',
                '成交量': 'volume',
            })
            
            # 格式化日期
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            # 估算资金流向
            df['main_inflow'] = df['volume'] * df['change_pct'] / 100
            df['sector_name'] = symbol
            
            # 取最近days天
            df = df.sort_values('date', ascending=False).head(days).reset_index(drop=True)
            
            return df[['date', 'sector_name', 'change_pct', 'main_inflow', 'close_price', 'volume']]
            
        except Exception as e:
            self.logger.error(f"获取恒生指数历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_all_sectors_historical(self, days: int = 30) -> pd.DataFrame:
        """批量获取所有板块的历史数据"""
        if self.use_etfs:
            sectors = list(HK_SECTOR_ETFS.keys())
        else:
            sectors = list(HSI_SECTOR_CODES.keys())
        
        all_data = []
        for sector in sectors:
            df = self.get_sector_historical(sector, days=days)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            return pd.DataFrame()
        
        return pd.concat(all_data, ignore_index=True)
