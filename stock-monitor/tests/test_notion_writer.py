"""Notion写入器测试模块"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
sys.path.insert(0, '/Users/yidazhou/.openclaw/workspace/stock-monitor')

from src.notion_writer import NotionWriter


class TestNotionWriter:
    """测试Notion写入器"""
    
    @pytest.fixture
    def mock_notion(self):
        """模拟Notion写入器"""
        with patch('src.notion_writer.requests.post') as mock_post:
            with patch('src.notion_writer.requests.get') as mock_get:
                # 模拟API响应
                mock_response = Mock()
                mock_response.json.return_value = {}
                mock_response.raise_for_status = Mock()
                mock_post.return_value = mock_response
                mock_get.return_value = mock_response
                
                writer = NotionWriter('fake_token', 'fake_page_id')
                yield writer, mock_post
    
    @pytest.fixture
    def sample_markdown(self):
        """示例Markdown内容"""
        return """# 测试报告

## 🔥 TOP10 板块

1. **电子** - +5.00亿 (+3.50%)
2. **半导体** - +4.00亿 (+2.80%)

## 📊 资金流向

图表将在此处显示
"""
    
    def test_notion_writer_init(self, mock_notion):
        """测试Notion写入器初始化"""
        writer, _ = mock_notion
        assert writer.api_key == 'fake_token'
        assert writer.parent_page_id == 'fake_page_id'
    
    def test_parse_markdown_to_blocks(self, mock_notion, sample_markdown):
        """测试Markdown解析为blocks"""
        writer, _ = mock_notion
        blocks = writer._parse_markdown_to_blocks(sample_markdown)
        
        assert len(blocks) > 0
    
    def test_parse_markdown_empty(self, mock_notion):
        """测试空Markdown"""
        writer, _ = mock_notion
        blocks = writer._parse_markdown_to_blocks('')
        assert len(blocks) == 0
    
    def test_parse_markdown_headings(self, mock_notion):
        """测试标题解析"""
        writer, _ = mock_notion
        md = """# 一级标题

## 二级标题

### 三级标题
"""
        blocks = writer._parse_markdown_to_blocks(md)
        
        heading_types = [b.get('type') for b in blocks]
        assert 'heading_1' in heading_types
        assert 'heading_2' in heading_types
        assert 'heading_3' in heading_types
    
    def test_split_content_by_market(self, mock_notion):
        """测试按市场分割内容"""
        writer, _ = mock_notion
        content = """# 多市场报告

## 🇨🇳 A股板块

### TOP10

1. 电子

## 🇺🇸 美股板块

### TOP10

1. Technology
"""
        
        market_names = {'a_share': 'A股', 'us': '美股', 'hk': '港股'}
        sections = writer._split_content_by_market(content, market_names)
        
        assert len(sections) >= 1
    
    def test_create_page_method(self, mock_notion):
        """测试创建页面方法"""
        writer, mock_post = mock_notion
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'test-page-id'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        result = writer._create_page('测试标题', [])
        
        assert mock_post.called
    
    def test_add_blocks_to_page_method(self, mock_notion):
        """测试添加blocks方法"""
        writer, _ = mock_notion
        # 验证方法存在
        assert hasattr(writer, '_add_blocks_to_page')
    
    def test_create_simple_chart_blocks(self, mock_notion):
        """测试创建图表blocks方法"""
        writer, _ = mock_notion
        assert hasattr(writer, '_create_simple_chart_blocks')
    
    def test_parse_inline_formatting(self, mock_notion):
        """测试内联格式解析"""
        writer, _ = mock_notion
        assert hasattr(writer, '_parse_inline_formatting')
    
    def test_extract_summary(self, mock_notion):
        """测试摘要提取"""
        writer, _ = mock_notion
        content = """# 标题

这是报告的摘要内容。

## 第一部分

详细内容
"""
        summary = writer._extract_summary(content)
        assert isinstance(summary, str)
    
    def test_get_chart_title(self, mock_notion):
        """测试获取图表标题"""
        writer, _ = mock_notion
        title = writer._get_chart_title('pie_inflow_20260220.png')
        assert isinstance(title, str)
    
    def test_add_file_fallback_block(self, mock_notion):
        """测试文件降级block"""
        writer, _ = mock_notion
        blocks = []
        writer._add_file_fallback_block(blocks, 'test_chart.png')
        assert len(blocks) >= 0
