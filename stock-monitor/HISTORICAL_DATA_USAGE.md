# 历史数据接口使用示例

本文档说明如何使用新增的历史数据接口功能。

## 1. DataFetcher - 数据获取模块

### 获取单个板块历史数据

```python
from src.data_fetcher import DataFetcher

fetcher = DataFetcher()

# 获取半导体板块最近30天的历史数据
df = fetcher.get_sector_flow_historical('半导体', days=30)

print(df.head())
# 输出列: date, sector_name, main_inflow, main_inflow_pct, change_pct, ...
```

### 批量获取多个板块历史数据

```python
sectors = ['半导体', '电池', '光伏', '电力', '有色']

# 批量获取，自动添加请求间隔防止限速
df = fetcher.get_all_sectors_historical(sectors, days=30)

# df包含所有板块的历史数据，通过sector_name列区分
for sector in sectors:
    sector_data = df[df['sector_name'] == sector]
    print(f"{sector}: {len(sector_data)} 条记录")
```

### 回填历史数据到指定日期范围

```python
# 从2024-02-07往前回溯10天的数据
sectors = ['半导体', '白酒', '银行']
df = fetcher.backfill_historical_data(sectors, end_date='2024-02-07', days=10)

# 保存到CSV供后续使用
df.to_csv('historical_data.csv', index=False, encoding='utf-8-sig')
```

## 2. SectorAnalyzer - 分析模块

### 加载日期范围数据

```python
from src.analyzer import SectorAnalyzer

analyzer = SectorAnalyzer(data_path='./data')

# 加载2024-01-01 至 2024-02-15的所有历史数据
df = analyzer.load_historical_range('2024-01-01', '2024-02-15')

print(f"共加载 {len(df)} 条记录")
print(f"日期范围: {df['date'].min()} 至 {df['date'].max()}")
```

### 计算板块趋势强度

```python
# 先加载历史数据
historical_df = analyzer.load_historical_range('2024-01-01', '2024-02-15')

# 计算半导体板块最近5天的趋势
trend = analyzer.calculate_trend_strength(historical_df, '半导体', days=5)

print(f"趋势得分: {trend['trend_score']}")  # -100 到 100
print(f"趋势方向: {trend['trend_direction']}")  # 'up', 'down', 'neutral'
print(f"平均净流入: {trend['avg_inflow']}")
print(f"上涨一致性: {trend['consistency']}")  # 0-1，越高说明连续上涨天数越多
print(f"动量: {trend['momentum']}")  # 近期相对于前期的变化

# 趋势得分解释：
# > 20: 上升趋势
# -20 ~ 20: 震荡/中性
# < -20: 下降趋势
```

## 3. ChartGenerator - 图表生成模块

### 加载历史数据（支持API回退）

```python
from src.chart_generator import ChartGenerator
from src.data_fetcher import DataFetcher

chart_gen = ChartGenerator(data_path='./data', charts_path='./charts')
fetcher = DataFetcher()

# 加载历史数据，如果本地缺失则从API获取补充
top_sectors = ['半导体', '电池', '光伏', '电力', '有色']
df = chart_gen.load_historical_data(
    days=30,
    data_fetcher=fetcher,  # 可选：提供data_fetcher用于获取缺失数据
    sectors=top_sectors     # 可选：指定板块列表
)
```

### 生成单个板块长期趋势图

```python
# 方法1: 自动加载数据生成图表
chart_path = chart_gen.generate_sector_history_chart('半导体', days=30)
print(f"图表已保存: {chart_path}")

# 方法2: 传入已加载的数据（避免重复加载）
historical_df = chart_gen.load_historical_data(days=60)
chart_path = chart_gen.generate_sector_history_chart('半导体', df=historical_df, days=30)

# 生成的图表包含：
# - 上半部分: 主力资金流向（带5日均线）
# - 下半部分: 每日涨跌幅
# - 底部统计: 平均净流入、总净流入、上涨天数
```

## 4. 综合使用示例：趋势分析报表

```python
from src.data_fetcher import DataFetcher
from src.analyzer import SectorAnalyzer
from src.chart_generator import ChartGenerator
import pandas as pd

def generate_sector_trend_report():
    """生成板块趋势分析报告"""

    # 初始化组件
    fetcher = DataFetcher()
    analyzer = SectorAnalyzer(data_path='./data')
    chart_gen = ChartGenerator(data_path='./data', charts_path='./charts')

    # 关注的板块列表
    watchlist = ['半导体', '电池', '光伏', '电力', '有色', '银行', '证券', '白酒']

    # 1. 获取历史数据
    print("正在获取历史数据...")
    historical_df = fetcher.get_all_sectors_historical(watchlist, days=20)

    # 2. 计算各板块趋势
    print("\n板块趋势分析:")
    print("-" * 60)

    results = []
    for sector in watchlist:
        trend = analyzer.calculate_trend_strength(historical_df, sector, days=5)

        if 'error' not in trend:
            results.append({
                'sector': sector,
                'trend_score': trend['trend_score'],
                'direction': trend['trend_direction'],
                'avg_inflow': trend['avg_inflow'],
                'consistency': trend['consistency']
            })

            direction_icon = "📈" if trend['trend_direction'] == 'up' else \
                           "📉" if trend['trend_direction'] == 'down' else "➡️"

            print(f"{direction_icon} {sector:10s} "
                  f"得分: {trend['trend_score']:6.1f} | "
                  f"平均净流入: {trend['avg_inflow']/1e8:6.2f}亿 | "
                  f"一致性: {trend['consistency']:.0%}")

    # 3. 找出最强/最弱趋势板块
    results_df = pd.DataFrame(results)
    if not results_df.empty:
        results_df = results_df.sort_values('trend_score', ascending=False)

        print("\n🏆 最强趋势板块:")
        for _, row in results_df.head(3).iterrows():
            print(f"   {row['sector']} (得分: {row['trend_score']:.1f})")

        print("\n⚠️ 最弱趋势板块:")
        for _, row in results_df.tail(3).iterrows():
            print(f"   {row['sector']} (得分: {row['trend_score']:.1f})")

    # 4. 生成趋势图表
    print("\n正在生成趋势图表...")
    for sector in watchlist[:3]:  # 只给前3个板块生成图表
        chart_path = chart_gen.generate_sector_history_chart(sector, df=historical_df, days=20)
        if chart_path:
            print(f"   ✓ {sector}: {chart_path}")

    return results_df

# 运行分析
if __name__ == '__main__':
    results = generate_sector_trend_report()
```

## 5. 注意事项

### 接口限速
- akshare接口有访问频率限制，代码已内置0.5秒的最小请求间隔
- 批量获取时会自动添加延迟，避免触发限制

### 数据存储
- 历史数据通过 `SectorAnalyzer.save_snapshot()` 保存到CSV
- 文件命名格式: `sector_flow_YYYYMMDD.csv`
- 图表生成器会自动尝试从API获取本地缺失的数据

### 交易日处理
- 日期范围加载会自动跳过周末
- 但API返回的数据只包含交易日，非交易日自然不会有数据

### 趋势得分解读
| 得分范围 | 趋势方向 | 建议 |
|---------|---------|------|
| > 50 | 强势上升 | 关注买入机会 |
| 20 ~ 50 | 温和上升 | 可持有观察 |
| -20 ~ 20 | 震荡/中性 | 观望 |
| -50 ~ -20 | 温和下降 | 注意风险 |
| < -50 | 强势下降 | 考虑回避 |
