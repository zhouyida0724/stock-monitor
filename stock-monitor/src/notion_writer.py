"""Notion输出模块 - 将监控数据写入Notion页面"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


class NotionWriter:
    """Notion写入器类 - 将监控报告写入Notion页面"""
    
    API_BASE = "https://api.notion.com/v1"
    API_VERSION = "2022-06-28"
    
    def __init__(self, api_key: str, parent_page_id: str):
        """
        初始化Notion写入器
        
        Args:
            api_key: Notion Integration API Key
            parent_page_id: 父页面ID（监控记录将创建在此页面下）
        """
        self.api_key = api_key
        self.parent_page_id = parent_page_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": self.API_VERSION,
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def write_report(self, title: str, content: str, database_id: Optional[str] = None, 
                     chart_files: Optional[list] = None, chart_urls: Optional[list] = None,
                     auto_upload_charts: bool = True) -> Optional[str]:
        """
        写入监控报告到Notion
        
        Args:
            title: 页面标题
            content: Markdown格式的报告内容
            database_id: 可选，如果提供则同时创建数据库条目
            chart_files: 可选，图表文件路径列表（会自动上传到Notion）
            chart_urls: 可选，图表URL列表（如果提供则优先使用外部图片，兼容旧版Imgur）
            auto_upload_charts: 是否自动将chart_files上传到Notion（默认True）
            
        Returns:
            Optional[str]: 创建的页面ID，失败返回None
        """
        try:
            # 解析Markdown内容为Notion blocks
            blocks = self._parse_markdown_to_blocks(content)
            
            # 如果有图表，添加图表部分
            if chart_files:
                chart_blocks = self._create_chart_blocks(chart_files, chart_urls, auto_upload_charts)
                blocks.extend(chart_blocks)
            
            # 创建页面
            page_id = self._create_page(title, blocks)
            
            if page_id and database_id:
                # 同时添加到数据库
                self._add_to_database(database_id, title, content)
            
            return page_id
            
        except Exception as e:
            self.logger.error(f"写入Notion失败: {str(e)}")
            return None
    
    def _create_page(self, title: str, blocks: list) -> Optional[str]:
        """
        在Notion中创建页面
        
        Args:
            title: 页面标题
            blocks: Notion block列表
            
        Returns:
            Optional[str]: 页面ID
        """
        url = f"{self.API_BASE}/pages"
        
        # 先创建空页面
        payload = {
            "parent": {"page_id": self.parent_page_id},
            "icon": {"type": "emoji", "emoji": "📊"},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            page_id = data.get("id")
            self.logger.info(f"成功创建Notion页面: {page_id}")
            
            # 然后分批添加blocks
            if blocks and page_id:
                self._add_blocks_to_page(page_id, blocks)
            
            return page_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"创建Notion页面请求失败: {str(e)}")
            raise
    
    def _add_blocks_to_page(self, page_id: str, blocks: list):
        """
        分批添加blocks到页面
        
        Args:
            page_id: 页面ID
            blocks: block列表
        """
        url = f"{self.API_BASE}/blocks/{page_id}/children"
        
        # Notion限制每次最多100个blocks
        batch_size = 90
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i+batch_size]
            payload = {"children": batch}
            
            try:
                response = requests.patch(url, headers=self.headers, json=payload, timeout=30)
                response.raise_for_status()
                self.logger.debug(f"已添加 {len(batch)} 个blocks")
            except requests.exceptions.HTTPError as e:
                self.logger.error(f"添加blocks失败: {str(e)}")
                # 打印详细的错误信息
                try:
                    error_detail = response.json()
                    self.logger.error(f"错误详情: {error_detail}")
                except:
                    self.logger.error(f"响应内容: {response.text}")
                # 继续添加剩余的blocks
                continue
            except requests.exceptions.RequestException as e:
                self.logger.error(f"添加blocks失败: {str(e)}")
                continue
    
    def _add_to_database(self, database_id: str, title: str, content: str) -> bool:
        """
        添加记录到数据库
        
        Args:
            database_id: 数据库ID
            title: 标题
            content: 内容摘要
            
        Returns:
            bool: 是否成功
        """
        url = f"{self.API_BASE}/pages"
        
        # 提取TOP3板块作为摘要
        summary = self._extract_summary(content)
        
        payload = {
            "parent": {"database_id": database_id},
            "icon": {"type": "emoji", "emoji": "📈"},
            "properties": {
                "名称": {"title": [{"text": {"content": title}}]},
                "日期": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
                "TOP板块": {"rich_text": [{"text": {"content": summary}}]},
                "状态": {"select": {"name": "已完成"}}
            }
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            self.logger.info("成功添加数据库记录")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"添加数据库记录失败: {str(e)}")
            return False
    
    def _parse_markdown_to_blocks(self, markdown: str) -> list:
        """
        将Markdown内容解析为Notion blocks
        
        Args:
            markdown: Markdown格式的报告
            
        Returns:
            list: Notion block列表
        """
        blocks = []
        lines = markdown.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 处理标题
            if line.startswith('# '):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('## '):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                    }
                })
            elif line.startswith('### '):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                    }
                })
            # 处理分隔线
            elif line == '---':
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
            # 处理列表项
            elif line.startswith('- ') or line.startswith('* '):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                    }
                })
            elif line.startswith('1. ') or (len(line) > 2 and line[0].isdigit() and '. ' in line[:5]):
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": line[line.find('. ')+2:]}}]
                    }
                })
            # 普通段落
            else:
                # 处理粗体 **text**
                rich_text = self._parse_inline_formatting(line)
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": rich_text}
                })
        
        return blocks
    
    def _parse_inline_formatting(self, text: str) -> list:
        """
        解析行内格式（粗体）
        
        Args:
            text: 文本
            
        Returns:
            list: rich_text列表
        """
        parts = []
        current = ""
        i = 0
        
        while i < len(text):
            if i < len(text) - 1 and text[i:i+2] == "**":
                if current:
                    parts.append({"type": "text", "text": {"content": current}})
                    current = ""
                # 找到结束**
                end = text.find("**", i+2)
                if end != -1:
                    parts.append({
                        "type": "text",
                        "text": {"content": text[i+2:end]},
                        "annotations": {"bold": True}
                    })
                    i = end + 2
                else:
                    current += text[i]
                    i += 1
            else:
                current += text[i]
                i += 1
        
        if current:
            parts.append({"type": "text", "text": {"content": current}})
        
        return parts if parts else [{"type": "text", "text": {"content": text}}]
    
    def _create_chart_blocks(self, chart_files: list, chart_urls: list = None, 
                             auto_upload: bool = True) -> list:
        """
        创建图表展示blocks
        
        Args:
            chart_files: 图表文件路径列表
            chart_urls: 图表URL列表（可选，如果提供则直接嵌入图片）
            auto_upload: 是否自动上传到Notion（默认True）
            
        Returns:
            list: Notion block列表
        """
        blocks = [
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            },
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 关键指标时间序列图"}}]
                }
            }
        ]
        
        chart_urls = chart_urls or []
        
        for i, chart_file in enumerate(chart_files):
            if not chart_file or not Path(chart_file).exists():
                continue
            
            chart_name = Path(chart_file).stem
            
            # 添加图表标题
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": self._get_chart_title(chart_name)}}]
                }
            })
            
            # 优先级1: 如果提供了外部URL，使用外部图片（保持兼容性）
            if i < len(chart_urls) and chart_urls[i]:
                blocks.append({
                    "object": "block",
                    "type": "image",
                    "image": {
                        "type": "external",
                        "external": {
                            "url": chart_urls[i]
                        }
                    }
                })
            # 优先级2: 自动上传到Notion
            elif auto_upload:
                file_upload_id = self.upload_image_to_notion(chart_file)
                if file_upload_id:
                    # 使用file_upload创建image block
                    blocks.append(self._create_image_block_with_file_upload(file_upload_id))
                else:
                    # 上传失败，显示文件路径说明
                    self._add_file_fallback_block(blocks, chart_file)
            # 优先级3: 显示本地文件路径
            else:
                self._add_file_fallback_block(blocks, chart_file)
        
        return blocks
    
    def _add_file_fallback_block(self, blocks: list, chart_file: str):
        """
        添加文件路径后备block（当上传失败时使用）
        
        Args:
            blocks: block列表
            chart_file: 图表文件路径
        """
        blocks.append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"图表文件: {chart_file}\n\n请查看本地文件系统中的图表。"}}
                ],
                "icon": {"type": "emoji", "emoji": "📈"},
                "color": "blue_background"
            }
        })
        
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": chart_file}}],
                "language": "plain text"
            }
        })
    
    def _get_chart_title(self, chart_name: str) -> str:
        """根据文件名获取图表标题"""
        if "top_sectors_trend" in chart_name:
            return "TOP板块资金流向趋势"
        elif "sector_comparison" in chart_name:
            return "板块对比分析"
        elif "market_heatmap" in chart_name:
            return "板块资金流向热力图"
        else:
            return "图表分析"
    
    def _extract_summary(self, content: str) -> str:
        """
        从报告中提取TOP3板块作为摘要
        
        Args:
            content: 报告内容
            
        Returns:
            str: 摘要
        """
        lines = content.split('\n')
        top3 = []
        
        for line in lines:
            if line.strip().startswith(('1.', '2.', '3.')) and '亿' in line:
                # 提取板块名称
                parts = line.split(' - ')
                if len(parts) > 0:
                    name = parts[0].split('. ')[-1] if '. ' in parts[0] else parts[0]
                    top3.append(name)
                    if len(top3) >= 3:
                        break
        
        return ' > '.join(top3) if top3 else '无数据'
    
    def create_monitoring_database(self, title: str = "板块监控记录") -> Optional[str]:
        """
        创建监控记录数据库
        
        Args:
            title: 数据库标题
            
        Returns:
            Optional[str]: 数据库ID
        """
        url = f"{self.API_BASE}/data_sources"
        
        payload = {
            "parent": {"page_id": self.parent_page_id},
            "title": [{"text": {"content": title}}],
            "properties": {
                "名称": {"title": {}},
                "日期": {"date": {}},
                "TOP板块": {"rich_text": {}},
                "状态": {
                    "select": {
                        "options": [
                            {"name": "监控中", "color": "yellow"},
                            {"name": "已完成", "color": "green"},
                            {"name": "异常", "color": "red"}
                        ]
                    }
                }
            },
            "is_inline": True
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            database_id = data.get("id")
            self.logger.info(f"成功创建数据库: {database_id}")
            return database_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"创建数据库失败: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试Notion API连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            url = f"{self.API_BASE}/users/me"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            self.logger.info("Notion API连接测试成功")
            return True
            
        except Exception as e:
            self.logger.error(f"Notion API连接测试失败: {str(e)}")
            return False
    
    def upload_image_to_notion(self, image_path: str) -> Optional[str]:
        """
        上传图片到Notion（3步上传流程）
        
        参考: https://developers.notion.com/guides/data-apis/uploading-small-files
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            Optional[str]: file_upload ID，失败返回None
        """
        try:
            file_path = Path(image_path)
            if not file_path.exists():
                self.logger.error(f"图片文件不存在: {image_path}")
                return None
            
            file_size = file_path.stat().st_size
            file_name = file_path.name
            file_ext = file_path.suffix.lower()
            
            # 确定MIME类型
            mime_type = "image/png"  # 默认
            if file_ext == ".jpg" or file_ext == ".jpeg":
                mime_type = "image/jpeg"
            elif file_ext == ".gif":
                mime_type = "image/gif"
            elif file_ext == ".webp":
                mime_type = "image/webp"
            
            self.logger.info(f"开始上传图片: {file_name} ({file_size} bytes)")
            
            # Step 1: 创建上传对象
            step1_url = f"{self.API_BASE}/file_uploads"
            step1_payload = {
                "name": file_name,
                "content_type": mime_type,
                "content_length": file_size
            }
            
            step1_headers = self.headers.copy()
            step1_headers["Content-Type"] = "application/json"
            
            response = requests.post(
                step1_url, 
                headers=step1_headers, 
                json=step1_payload, 
                timeout=30
            )
            response.raise_for_status()
            step1_data = response.json()
            
            file_upload_id = step1_data.get("id")
            upload_url = step1_data.get("upload_url")
            
            if not file_upload_id or not upload_url:
                self.logger.error(f"创建上传对象失败: {step1_data}")
                return None
            
            self.logger.debug(f"上传对象创建成功: {file_upload_id}")
            
            # Step 2: 上传文件内容 (multipart/form-data)
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f, mime_type)}
                upload_headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Notion-Version": self.API_VERSION
                }
                upload_response = requests.post(
                    upload_url,
                    headers=upload_headers,
                    files=files,
                    timeout=60
                )
                upload_response.raise_for_status()
            
            self.logger.debug(f"文件内容上传成功")
            
            # Step 3: 返回file_upload ID用于创建image block
            self.logger.info(f"图片上传完成: {file_name} -> {file_upload_id}")
            return file_upload_id
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"上传图片请求失败: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"上传图片失败: {str(e)}")
            return None
    
    def _create_image_block_with_file_upload(self, file_upload_id: str) -> Dict[str, Any]:
        """
        创建使用file_upload的image block
        
        Args:
            file_upload_id: Notion file_upload ID
            
        Returns:
            Dict: image block对象
        """
        return {
            "object": "block",
            "type": "image",
            "image": {
                "type": "file_upload",
                "file_upload": {
                    "id": file_upload_id
                }
            }
        }
