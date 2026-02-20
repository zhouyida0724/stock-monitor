# Stock-Monitor 重构计划

## 📊 代码审查结果

### 一、死代码 (Dead Code)

| 文件 | 问题 | 建议 |
|------|------|------|
| `src/data_fetcher.py` | 与 `data_fetchers/a_share_fetcher.py` 功能重复，仅被 `main.py` 和 `generate_historical_report.py` 使用 | 迁移到 DataFetcherFactory 后删除 |
| `src/scheduler.py` | 被 `main.py` 使用，`multi_market_scheduler.py` 是更完整的替代品 | 标记为 deprecated，后期删除 |
| `main.py` | 旧入口，仅支持 A股，`run_multi_market.py` 是替代 | 标记 deprecated 或删除 |
| `src/multi_market_scheduler.py` | 导入了 `ImageUploader` 但从未使用 | 删除未使用的 import |
| `generate_historical_report.py` | 使用旧的 `data_fetcher.py`，可用于历史回测但非核心功能 | 保留或迁移到新架构 |

### 二、测试覆盖缺失

| 模块 | 测试状态 | 优先级 |
|------|----------|--------|
| `chart_generator.py` | ❌ 无测试 | **高** |
| `notion_writer.py` | ❌ 无测试 | **高** |
| `image_uploader.py` | ❌ 无测试 | 中 |
| `us_market_fetcher.py` | ❌ 无测试 | **高** |
| `hk_market_fetcher.py` | ❌ 无测试 | **高** |
| `a_share_fetcher.py` | ⚠️ 部分覆盖 (via data_fetchers.py) | 中 |
| `reporter.py` | ⚠️ 部分覆盖 | 中 |
| `analyzer.py` | ✅ 完整覆盖 | - |

---

## 🛠️ 重构步骤

### Phase 1: 清理死代码 (1-2天)

1. **移除未使用的 import**
   ```python
   # src/multi_market_scheduler.py
   # 删除: from .image_uploader import ImageUploader
   # 删除: image_uploader: Optional[ImageUploader] = None
   ```

2. **标记 deprecated 入口点**
   - 在 `main.py` 开头添加弃用警告
   - 在 `scheduler.py` 开头添加弃用警告

3. **统一数据获取接口**
   - 将 `generate_historical_report.py` 迁移到使用 `DataFetcherFactory`
   - 然后删除 `data_fetcher.py`

### Phase 2: 补充测试覆盖 (2-3天)

1. **chart_generator.py** (最高优先级)
   - `test_generate_top_sectors_trend`
   - `test_generate_sector_flow_pie_charts`
   - `test_generate_market_flow_summary_chart`
   - `test_generate_market_top_sectors_trend`

2. **us_market_fetcher.py / hk_market_fetcher.py**
   - `test_fetch_with_retry_success`
   - `test_fetch_with_retry_fallback_to_cache`
   - `test_rate_limit`

3. **notion_writer.py**
   - `test_write_report`
   - `test_parse_markdown_to_blocks`

### Phase 3: 代码优化 (可选)

1. 合并相似的数据获取逻辑
2. 抽取公共工具函数到 `utils.py`
3. 统一错误处理和日志格式

---

## 📋 详细任务清单

- [x] 1. 删除 `multi_market_scheduler.py` 中未使用的 ImageUploader import
- [x] 2. 在 `main.py` 添加入口弃用提示
- [x] 3. 迁移 `generate_historical_report.py` 使用 DataFetcherFactory
- [x] 4. 修复单市场 Notion 报告图表上传功能
- [x] 5. ~~删除 `data_fetcher.py`~~ (保留，用于向后兼容 main.py/scheduler.py)
- [x] 6. ~~删除 `scheduler.py`~~ (保留，标记 deprecated)
- [x] 7. 为 `chart_generator.py` 添加单元测试 (14 tests)
- [x] 8. 为 `us_market_fetcher.py` 添加单元测试 (已有，包含在 test_data_fetchers.py)
- [x] 9. 为 `hk_market_fetcher.py` 添加单元测试 (已有，包含在 test_data_fetchers.py)
- [x] 10. 为 `notion_writer.py` 添加单元测试 (12 tests)

---

## 🔍 额外发现

1. **重复代码**: `data_fetcher.py` 和 `data_fetchers/a_share_fetcher.py` 几乎做同样的事
2. **入口混乱**: 三个入口文件 (`main.py`, `run_multi_market.py`, `generate_historical_report.py`)
3. **ImageUploader 未使用**: 在 `multi_market_scheduler.py` 中导入但从未调用
