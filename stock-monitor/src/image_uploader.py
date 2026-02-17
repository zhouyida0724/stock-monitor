"""图床上传模块 - 上传图表到Imgur获取公开URL"""
import logging
import base64
from pathlib import Path
from typing import Optional
import requests

logger = logging.getLogger(__name__)


class ImageUploader:
    """图片上传器类 - 支持Imgur等图床"""
    
    def __init__(self, imgur_client_id: Optional[str] = None):
        """
        初始化上传器
        
        Args:
            imgur_client_id: Imgur API Client ID (可选)
        """
        self.imgur_client_id = imgur_client_id
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def upload_to_imgur(self, image_path: str) -> Optional[str]:
        """
        上传图片到Imgur
        
        Args:
            image_path: 本地图片路径
            
        Returns:
            Optional[str]: 图片URL，失败返回None
        """
        if not self.imgur_client_id:
            self.logger.warning("未配置Imgur Client ID，跳过上传")
            return None
        
        try:
            # 读取图片文件
            image_file = Path(image_path)
            if not image_file.exists():
                self.logger.error(f"图片文件不存在: {image_path}")
                return None
            
            with open(image_file, 'rb') as f:
                image_data = base64.b64encode(f.read())
            
            # 上传到Imgur
            url = "https://api.imgur.com/3/image"
            headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
            payload = {"image": image_data}
            
            self.logger.info(f"正在上传图片到Imgur: {image_path}")
            response = requests.post(url, headers=headers, data=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if data.get("success"):
                image_url = data["data"]["link"]
                self.logger.info(f"图片上传成功: {image_url}")
                return image_url
            else:
                self.logger.error(f"Imgur上传失败: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"上传请求失败: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"上传图片失败: {str(e)}")
            return None
    
    def upload_file(self, file_path: str, provider: str = "imgur") -> Optional[str]:
        """
        通用上传接口
        
        Args:
            file_path: 文件路径
            provider: 上传服务提供商
            
        Returns:
            Optional[str]: 文件URL
        """
        if provider == "imgur":
            return self.upload_to_imgur(file_path)
        else:
            self.logger.warning(f"不支持的上传服务: {provider}")
            return None
    
    def test_imgur_connection(self) -> bool:
        """
        测试Imgur连接
        
        Returns:
            bool: 连接是否成功
        """
        if not self.imgur_client_id:
            return False
        
        try:
            url = "https://api.imgur.com/3/credits"
            headers = {"Authorization": f"Client-ID {self.imgur_client_id}"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            self.logger.info("Imgur API连接测试成功")
            return True
        except Exception as e:
            self.logger.error(f"Imgur API连接测试失败: {str(e)}")
            return False
