"""报告生成模块 - 生成Markdown格式报告"""
import logging
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器类
    
    支持单市场报告和多市场综合报告生成
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_markdown(self, ranking_df: pd.DataFrame, rotation_list: List[Dict]) -> str:
        """生成单市场Markdown格式报告（兼容旧版本）
        
        Args:
            ranking_df: TOP10排名数据
            rotation_list: 轮动信号列表
            
        Returns:
            str: Markdown格式报告
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        lines = [
            f"📊 **板块资金流向监控 - {today}**",
            "",
            "🔥 **TOP10 板块（按净流入）：**",
            ""
        ]
        
        # 添加TOP10列表
        if ranking_df is not None and not ranking_df.empty:
            for idx, row in ranking_df.iterrows():
                rank = idx + 1
                
                # 获取板块名
                sector_name = row.get('sector_name', row.get('name', f'板块{rank}'))
                
                # 获取净流入（转换为亿元）
                inflow = self._get_inflow_value(row)
                
                # 获取涨跌幅
                change_pct = row.get('change_pct', row.get('今日涨跌幅', 0))
                
                lines.append(f"{rank}. {sector_name} - {inflow:+.2f}亿 ({change_pct:+.2f}%)")
        else:
            lines.append("_暂无数据_")
        
        lines.append("")
        
        # 添加轮动信号
        lines.append("🔄 **轮动信号（今日新进入TOP10）：**")
        lines.append("")
        
        if rotation_list:
            for signal in rotation_list:
                sector = signal['sector_name']
                prev_rank = signal['yesterday_rank']
                if isinstance(prev_rank, int):
                    lines.append(f"- {sector}（昨日排名：#{prev_rank}）")
                else:
                    lines.append(f"- {sector}（昨日排名：{prev_rank}）")
        else:
            lines.append("_今日无新进入TOP10的板块_")
        
        lines.append("")
        lines.append("---")
        lines.append(f"_数据更新时间：{datetime.now().strftime('%H:%M:%S')}_")
        
        return '\n'.join(lines)
    
    def generate_multi_markdown(self, market_results: Dict[str, Dict]) -> str:
        """生成多市场综合Markdown报告
        
        Args:
            market_results: 各市场的运行结果字典
                {
                    'a_share': {'success': True, 'top10': df, 'rotation_signals': [...]},
                    'us': {...},
                    'hk': {...}
                }
                
        Returns:
            str: Markdown格式综合报告
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        lines = [
            f"# 📊 多市场板块监控 - {today}",
            ""
        ]
        
        # A股部分
        if 'a_share' in market_results:
            lines.extend(self._generate_market_section(
                market_results['a_share'],
                "🇨🇳 A股板块资金流向",
                "A股"
            ))
        
        # 美股部分
        if 'us' in market_results:
            lines.extend(self._generate_market_section(
                market_results['us'],
                "🇺🇸 美股板块表现 (Sector ETFs)",
                "美股"
            ))
        
        # 港股部分
        if 'hk' in market_results:
            lines.extend(self._generate_market_section(
                market_results['hk'],
                "🇭🇰 港股行业指数",
                "港股"
            ))
        
        # 总结
        lines.append("---")
        lines.append("")
        lines.append(f"_报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_")
        
        return '\n'.join(lines)
    
    def _generate_market_section(self, result: Dict, title: str, market_name: str) -> List[str]:
        """生成单个市场的报告部分
        
        Args:
            result: 市场运行结果
            title: 章节标题
            market_name: 市场名称（用于日志）
            
        Returns:
            List[str]: Markdown行列表
        """
        lines = [
            f"## {title}",
            ""
        ]
        
        if not result.get('success', False):
            error_msg = result.get('error', '未知错误')
            lines.append(f"⚠️ **获取失败**: {error_msg}")
            lines.append("")
            return lines
        
        top10_df = result.get('top10')
        rotation_list = result.get('rotation_signals', [])
        
        # TOP10排名
        lines.append("### 🔥 TOP10 排名")
        lines.append("")
        
        if top10_df is not None and not top10_df.empty:
            for idx, row in top10_df.head(10).iterrows():
                rank = idx + 1
                sector_name = row.get('sector_name', row.get('name', f'板块{rank}'))
                inflow = self._get_inflow_value(row)
                change_pct = row.get('change_pct', row.get('今日涨跌幅', 0))
                
                # 添加ETF代码（美股/港股）
                symbol = row.get('symbol', '')
                if symbol:
                    lines.append(f"{rank}. **{sector_name}** ({symbol}) - {inflow:+.2f}亿 ({change_pct:+.2f}%)")
                else:
                    lines.append(f"{rank}. **{sector_name}** - {inflow:+.2f}亿 ({change_pct:+.2f}%)")
        else:
            lines.append("_暂无数据_")
        
        lines.append("")
        
        # 轮动信号
        lines.append("### 🔄 轮动信号")
        lines.append("")
        
        if rotation_list:
            for signal in rotation_list:
                sector = signal['sector_name']
                prev_rank = signal['yesterday_rank']
                if isinstance(prev_rank, int):
                    lines.append(f"- 📈 **{sector}**（昨日排名：#{prev_rank}）")
                else:
                    lines.append(f"- 📈 **{sector}**（昨日排名：{prev_rank}）")
        else:
            lines.append("_今日无新进入TOP10的板块_")
        
        lines.append("")
        
        return lines
    
    def _get_inflow_value(self, row) -> float:
        """从行数据中提取净流入值（转换为亿元）"""
        inflow = 0
        
        # 尝试各种可能的列名
        for col in ['main_inflow', 'super_large_inflow', '今日主力净流入-净额', '今日超大单净流入-净额']:
            if col in row and pd.notna(row[col]) and row[col] != 0:
                val = row[col]
                # 判断单位：如果是美股/港股的估算值，通常较小
                if abs(val) < 1000000:  # 小于100万，可能是每股价格*股数
                    inflow = val / 1e4  # 转换为亿元（简化）
                else:
                    inflow = val / 1e8  # A股单位是分，转换为亿元
                break
        
        return inflow
    
    def generate_summary(self, ranking_df: pd.DataFrame) -> str:
        """生成简短摘要（用于日志）
        
        Args:
            ranking_df: 排名数据
            
        Returns:
            str: 简短摘要
        """
        if ranking_df is None or ranking_df.empty:
            return "无数据"
        
        top3 = []
        for idx, row in ranking_df.head(3).iterrows():
            sector_name = row.get('sector_name', row.get('name', f'板块{idx+1}'))
            top3.append(sector_name)
        
        return f"TOP3: {' > '.join(top3)}"
    
    def generate_market_summary(self, market_results: Dict[str, Dict]) -> str:
        """生成多市场摘要
        
        Args:
            market_results: 各市场的运行结果
            
        Returns:
            str: 多市场摘要
        """
        summaries = []
        
        market_names = {
            'a_share': 'A股',
            'us': '美股',
            'hk': '港股'
        }
        
        for market, result in market_results.items():
            if result.get('success') and result.get('top10') is not None:
                market_name = market_names.get(market, market)
                top3 = []
                for idx, row in result['top10'].head(3).iterrows():
                    sector = row.get('sector_name', row.get('name', f'板块{idx+1}'))
                    top3.append(sector)
                summaries.append(f"{market_name}: {' > '.join(top3)}")
        
        return ' | '.join(summaries) if summaries else "无数据"
