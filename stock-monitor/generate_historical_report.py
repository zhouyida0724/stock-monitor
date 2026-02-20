#!/usr/bin/env python3
"""
生成2026年1月1日至现在的历史数据报表到Notion

⚠️ 已弃用: 此脚本使用旧的数据获取器，建议使用 run_multi_market.py
"""
import sys
import asyncio
sys.path.insert(0, '.')

import logging
from datetime import datetime, timedelta
from src.config import get_settings
from src.data_fetchers import DataFetcherFactory, MarketType
from src.analyzer import SectorAnalyzer
from src.chart_generator import ChartGenerator
from src.notion_writer import NotionWriter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def generate_historical_report():
    """生成历史数据报表"""
    
    settings = get_settings()
    
    # 初始化组件 - 使用 DataFetcherFactory
    fetcher = DataFetcherFactory.create(MarketType.A_SHARE)
    analyzer = SectorAnalyzer(data_path=settings.DATA_PATH)
    chart_gen = ChartGenerator(data_path=settings.DATA_PATH, charts_path='./charts')
    notion = NotionWriter(
        api_key=settings.NOTION_API_KEY,
        parent_page_id=settings.NOTION_PARENT_PAGE_ID
    )
    
    # 日期范围：2026年1月1日到现在
    start_date = '2026-01-01'
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"=" * 60)
    logger.info(f"生成历史数据报表: {start_date} 至 {end_date}")
    logger.info(f"=" * 60)
    
    # 1. 获取今日板块列表（用于确定要获取历史的板块）
    logger.info("获取当前板块列表...")
    today_df = fetcher.get_sector_data()
    top_sectors = today_df.nlargest(20, 'main_inflow')['sector_name'].tolist()
    logger.info(f"关注板块: {', '.join(top_sectors[:10])}...")
    
    # 2. 回填历史数据
    logger.info(f"\n回填历史数据（{start_date} 至 {end_date}）...")
    historical_df = fetcher.backfill_historical_data(
        sectors=top_sectors[:15],  # 前15个板块，避免请求过多
        end_date=end_date,
        days=47  # 1月1日到2月16日约47天
    )
    
    if historical_df.empty:
        logger.error("未能获取历史数据")
        return False
    
    logger.info(f"获取到 {len(historical_df)} 条历史记录")
    logger.info(f"日期范围: {historical_df['date'].min()} 至 {historical_df['date'].max()}")
    
    # 3. 保存数据快照
    logger.info("\n保存数据到CSV...")
    for date in historical_df['date'].unique():
        day_data = historical_df[historical_df['date'] == date]
        analyzer.save_snapshot(day_data, date)
    
    # 4. 计算各板块趋势
    logger.info("\n分析板块趋势...")
    trend_results = []
    
    for sector in top_sectors[:15]:
        try:
            trend = analyzer.calculate_trend_strength(historical_df, sector, days=10)
            if trend and 'error' not in trend:
                trend_results.append({
                    'sector': sector,
                    'trend_score': float(trend['trend_score']),
                    'direction': trend['trend_direction'],
                    'avg_inflow': float(trend['avg_inflow']),
                    'consistency': float(trend['consistency']),
                    'momentum': float(trend['momentum'])
                })
        except Exception as e:
            logger.warning(f"计算 {sector} 趋势失败: {e}")
            continue
    
    # 排序
    if trend_results:
        trend_results.sort(key=lambda x: x['trend_score'], reverse=True)
        logger.info(f"成功计算 {len(trend_results)} 个板块的趋势")
    else:
        logger.warning("未能计算任何板块的趋势")
    
    # 5. 生成图表
    logger.info("\n生成趋势图表...")
    chart_files = []
    
    # 生成整体市场趋势图
    trend_chart = chart_gen.generate_top_sectors_trend(top_n=5, days=47)
    if trend_chart:
        chart_files.append(trend_chart)
        logger.info(f"  ✓ TOP5趋势图: {trend_chart}")
    
    # 生成热力图
    heatmap_chart = chart_gen.generate_market_heatmap(days=20)
    if heatmap_chart:
        chart_files.append(heatmap_chart)
        logger.info(f"  ✓ 热力图: {heatmap_chart}")
    
    # 生成单个板块历史图（最强和最弱各2个）
    if trend_results and len(trend_results) >= 4:
        sectors_to_chart = [
            trend_results[0]['sector'], 
            trend_results[1]['sector'], 
            trend_results[-1]['sector'], 
            trend_results[-2]['sector']
        ]
        for sector in sectors_to_chart:
            try:
                chart_path = chart_gen.generate_sector_history_chart(sector, df=historical_df, days=47)
                if chart_path:
                    chart_files.append(chart_path)
                    logger.info(f"  ✓ {sector}历史图")
            except Exception as e:
                logger.warning(f"生成 {sector} 图表失败: {e}")
    
    # 6. 生成Markdown报告
    logger.info("\n生成报告...")
    
    # 获取统计信息
    unique_dates = historical_df['date'].nunique() if 'date' in historical_df.columns else 0
    total_records = len(historical_df)
    
    report_lines = [
        f"# 📊 板块资金流向历史分析报告",
        f"",
        f"**分析周期**: {start_date} 至 {end_date}",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**数据范围**: 板块历史资金流（日级别）",
        f"**交易日数量**: {unique_dates} 天",
        f"**数据记录**: {total_records} 条",
        f"",
        f"---",
        f"",
    ]
    
    if trend_results:
        report_lines.extend([
            f"## 🔥 TOP10 板块趋势排名",
            f"",
            "| 排名 | 板块 | 趋势得分 | 方向 | 平均净流入 | 上涨一致性 |",
            "|------|------|----------|------|------------|------------|",
        ])
        
        for i, r in enumerate(trend_results[:10], 1):
            direction_icon = "📈" if r['direction'] == 'up' else "📉" if r['direction'] == 'down' else "➡️"
            report_lines.append(
                f"| {i} | {r['sector']} | {r['trend_score']:.1f} | {direction_icon} {r['direction']} | "
                f"{r['avg_inflow']/1e8:.2f}亿 | {r['consistency']:.0%} |"
            )
        
        report_lines.extend([
            f"",
            f"---",
            f"",
            f"## 🏆 强势板块（趋势得分 > 20）",
            f"",
        ])
        
        strong_sectors = [r for r in trend_results if r['trend_score'] > 20]
        if strong_sectors:
            for r in strong_sectors[:5]:
                report_lines.append(f"- **{r['sector']}**: 得分 {r['trend_score']:.1f}，平均净流入 {r['avg_inflow']/1e8:.2f}亿")
        else:
            report_lines.append("暂无强势板块")
        
        report_lines.extend([
            f"",
            f"## ⚠️ 弱势板块（趋势得分 < -20）",
            f"",
        ])
        
        weak_sectors = [r for r in trend_results if r['trend_score'] < -20]
        if weak_sectors:
            for r in weak_sectors[-5:]:
                report_lines.append(f"- **{r['sector']}**: 得分 {r['trend_score']:.1f}，平均净流入 {r['avg_inflow']/1e8:.2f}亿")
        else:
            report_lines.append("暂无弱势板块")
    else:
        report_lines.extend([
            f"## ⚠️ 趋势分析",
            f"",
            f"未能计算板块趋势，请检查数据完整性。",
            f"",
        ])
    
    # 关键发现
    report_lines.extend([
        f"",
        f"---",
        f"",
        f"## 📈 关键发现",
        f"",
        f"1. **分析期间共 {unique_dates} 个交易日**",
    ])
    
    if trend_results:
        strong_sectors = [r for r in trend_results if r['trend_score'] > 20]
        weak_sectors = [r for r in trend_results if r['trend_score'] < -20]
        report_lines.extend([
            f"2. **趋势最强板块**: {trend_results[0]['sector']} (得分: {trend_results[0]['trend_score']:.1f})",
            f"3. **趋势最弱板块**: {trend_results[-1]['sector']} (得分: {trend_results[-1]['trend_score']:.1f})",
            f"4. **强势板块数量**: {len(strong_sectors)} 个",
            f"5. **弱势板块数量**: {len(weak_sectors)} 个",
        ])
    else:
        report_lines.append(f"2. **趋势分析**: 暂无法计算")
    
    report_lines.extend([
        f"",
        f"---",
        f"",
        f"## 📊 图表说明",
        f"",
        f"本报告包含以下图表：",
        f"- TOP5板块资金流向趋势图",
        f"- 板块资金流向热力图（近20天）",
    ])
    
    if trend_results and len(trend_results) >= 4:
        report_lines.append(f"- 最强/最弱板块历史趋势图")
    
    report_lines.append(f"")
    
    report_content = '\n'.join(report_lines)
    
    # 7. 写入Notion
    logger.info("\n写入Notion...")
    title = f"📊 板块资金流向历史分析 - {start_date} 至 {end_date}"
    
    try:
        page_id = notion.write_report(
            title=title,
            content=report_content,
            chart_files=chart_files
        )
        
        if page_id:
            logger.info(f"✅ 报告已成功写入Notion!")
            logger.info(f"   页面ID: {page_id}")
            return True
        else:
            logger.error("写入Notion失败")
            return False
            
    except Exception as e:
        logger.error(f"写入Notion失败: {e}")
        return False

if __name__ == '__main__':
    success = asyncio.run(generate_historical_report())
    sys.exit(0 if success else 1)
