"""美股数据获取器 - 基于yfinance获取Sector SPDR ETFs"""
import logging
import time
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .base import BaseDataFetcher, MarketType

try:
    import yfinance as yf
except ImportError:
    yf = None


# 重试配置
MAX_RETRIES = 3
BASE_DELAY = 2  # 基础延迟秒数
REQUEST_INTERVAL = 1.5  # 每次请求间隔秒数


# Sector SPDR ETFs 映射
SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Consumer Discretionary": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


class USMarketDataFetcher(BaseDataFetcher):
    """美股板块数据获取器
    
    使用yfinance获取Sector SPDR ETFs数据作为板块代理
    通过涨跌幅和成交量估算资金流向
    """
    
    def __init__(self):
        super().__init__()
        self.market_type = MarketType.US
        self.sector_etfs = SECTOR_ETFS
        self._last_request_time = 0
        self._cache = {}  # 简单缓存
        
        if yf is None:
            raise ImportError("请安装yfinance: pip install yfinance")
    
    def _rate_limit(self):
        """请求频率限制"""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()
    
    def _fetch_with_retry(self, symbol: str, period: str = "5d"):
        """带重试的数据获取
        
        Args:
            symbol: ETF代码
            period: 数据周期
            
        Returns:
            DataFrame 或 None
        """
        for attempt in range(MAX_RETRIES):
            try:
                self._rate_limit()
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                
                # 成功获取，更新缓存
                if not hist.empty:
                    self._cache[symbol] = {
                        'data': hist.copy(),
                        'timestamp': datetime.now()
                    }
                
                return hist
                
            except Exception as e:
                if "Rate limited" in str(e) or "Too Many Requests" in str(e):
                    delay = BASE_DELAY * (2 ** attempt)  # 指数退避
                    self.logger.warning(f"{symbol} 请求被限流，{delay}秒后重试 (第{attempt+1}/{MAX_RETRIES}次)...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"{symbol} 获取失败: {e}")
                    break
        
        # 所有重试失败，返回缓存数据（如果有且不太旧）
        if symbol in self._cache:
            cache_age = (datetime.now() - self._cache[symbol]['timestamp']).total_seconds()
            if cache_age < 3600:  # 缓存1小时内有效
                self.logger.info(f"{symbol} 使用缓存数据（{cache_age:.0f}秒前）")
                return self._cache[symbol]['data']
        
        return None
    
    def get_sector_data(self, trade_date: Optional[str] = None) -> pd.DataFrame:
        """获取美股板块数据（Sector ETFs当日数据）
        
        通过yfinance获取Sector SPDR ETFs的最新数据
        使用涨跌幅和成交量变化估算资金流向
        
        Args:
            trade_date: 交易日期，格式 YYYYMMDD（yfinance忽略此参数，获取最新数据）
            
        Returns:
            pd.DataFrame: 板块数据，包含：
                - sector_name: 板块名称
                - symbol: ETF代码
                - change_pct: 涨跌幅
                - main_inflow: 估算资金流向（基于价格变化和成交量）
                - volume: 成交量
                - close_price: 收盘价
        """
        try:
            self.logger.info(f"正在获取美股Sector ETFs数据...")
            
            data_list = []
            
            for sector_name, symbol in self.sector_etfs.items():
                try:
                    # 使用带重试的获取方法
                    hist = self._fetch_with_retry(symbol, period="5d")
                    
                    if hist is None or hist.empty or len(hist) < 1:
                        self.logger.warning(f"无法获取 {symbol} 数据")
                        continue
                    
                    # 获取最新数据
                    latest = hist.iloc[-1]
                    prev_close = hist.iloc[-2]['Close'] if len(hist) >= 2 else latest['Open']
                    
                    # 计算涨跌幅
                    change_pct = ((latest['Close'] - prev_close) / prev_close) * 100
                    
                    # 获取成交量
                    volume = int(latest['Volume'])
                    
                    # 估算资金流向：使用价格变化 * 成交量作为代理指标
                    # 正向变化 = 资金流入，负向变化 = 资金流出
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
                raise ValueError("无法获取任何Sector ETFs数据")
            
            df = pd.DataFrame(data_list)
            
            # 按估算资金流向排序
            df = df.sort_values('main_inflow', ascending=False).reset_index(drop=True)
            
            # 添加日期
            df['trade_date'] = trade_date or datetime.now().strftime('%Y%m%d')
            
            self.logger.info(f"成功获取 {len(df)} 个美股板块数据")
            return df
            
        except Exception as e:
            self.logger.error(f"获取美股数据失败: {str(e)}")
            raise
    
    def get_sector_historical(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """获取单个Sector ETF的历史数据
        
        Args:
            symbol: ETF代码（如"XLK"）或板块名称（如"Technology"）
            days: 获取最近多少天的数据
            
        Returns:
            pd.DataFrame: 历史数据，包含：
                - date: 日期
                - sector_name: 板块名称
                - symbol: ETF代码
                - main_inflow: 估算资金流向
                - change_pct: 涨跌幅
                - close_price: 收盘价
                - volume: 成交量
        """
        try:
            # 如果传入的是板块名称，转换为ETF代码
            if symbol in self.sector_etfs:
                sector_name = symbol
                etf_symbol = self.sector_etfs[symbol]
            else:
                # 反向查找
                etf_symbol = symbol.upper()
                sector_name = None
                for name, sym in self.sector_etfs.items():
                    if sym == etf_symbol:
                        sector_name = name
                        break
                if sector_name is None:
                    sector_name = etf_symbol
            
            self.logger.info(f"正在获取 {etf_symbol} ({sector_name}) 的历史数据...")
            
            # 使用带重试的获取方法
            hist = self._fetch_with_retry(etf_symbol, period=f"{days + 5}d")
            
            if hist is None or hist.empty:
                self.logger.warning(f"无法获取 {etf_symbol} 历史数据")
                return pd.DataFrame()
            
            # 重置索引，将Date转换为列
            hist = hist.reset_index()
            hist['Date'] = pd.to_datetime(hist['Date']).dt.strftime('%Y-%m-%d')
            
            # 计算每日变化百分比和估算资金流向
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
            
            # 按日期降序，取最近days天
            df = df.sort_values('date', ascending=False).head(days).reset_index(drop=True)
            
            self.logger.info(f"成功获取 {sector_name} 历史数据 {len(df)} 条")
            return df
            
        except Exception as e:
            self.logger.error(f"获取 {symbol} 历史数据失败: {str(e)}")
            return pd.DataFrame()
    
    def get_all_sectors_historical(self, days: int = 30) -> pd.DataFrame:
        """批量获取所有Sector ETFs的历史数据
        
        Args:
            days: 获取最近多少天的数据
            
        Returns:
            pd.DataFrame: 合并后的历史数据
        """
        all_data = []
        
        for sector_name in self.sector_etfs.keys():
            df = self.get_sector_historical(sector_name, days=days)
            if not df.empty:
                all_data.append(df)
        
        if not all_data:
            self.logger.warning("未获取到任何Sector ETFs历史数据")
            return pd.DataFrame()
        
        combined = pd.concat(all_data, ignore_index=True)
        self.logger.info(f"批量获取完成，共 {len(self.sector_etfs)} 个板块，{len(combined)} 条记录")
        return combined
    
    def get_etf_info(self, symbol: str) -> dict:
        """获取ETF详细信息
        
        Args:
            symbol: ETF代码
            
        Returns:
            dict: ETF信息
        """
        try:
            self._rate_limit()
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return {
                'symbol': symbol,
                'name': info.get('shortName', ''),
                'category': info.get('category', ''),
                'total_assets': info.get('totalAssets', 0),
            }
        except Exception as e:
            self.logger.error(f"获取ETF信息失败: {e}")
            return {}
