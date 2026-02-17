"""配置模块 - 使用Pydantic管理配置"""
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """应用配置类"""
    
    # Telegram配置（可选）
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # Notion配置（可选）
    NOTION_API_KEY: Optional[str] = None
    NOTION_PARENT_PAGE_ID: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None
    
    # Imgur图床配置（可选）
    IMGUR_CLIENT_ID: Optional[str] = None
    
    # 输出模式: "telegram", "notion", "both"
    OUTPUT_MODE: str = "notion"
    
    # 调度配置
    SCHEDULE_TIME: str = "15:05"
    
    # 数据路径
    DATA_PATH: str = "./data"
    
    # ==================== 多市场配置 ====================
    
    # 启用哪些市场
    ENABLED_MARKETS: str = "a_share,us,hk"  # 逗号分隔: a_share,us,hk
    
    # A股配置
    A_SHARE_ENABLED: bool = True
    A_SHARE_SCHEDULE_TIME: str = "15:05"
    A_SHARE_DAYS_OF_WEEK: str = "mon-fri"
    
    # 美股配置
    US_ENABLED: bool = True
    US_SCHEDULE_TIME: str = "06:00"  # 北京时间早上（美股收盘后）
    US_DAYS_OF_WEEK: str = "tue-sat"  # 美股周一至周五
    
    # 港股配置
    HK_ENABLED: bool = True
    HK_SCHEDULE_TIME: str = "16:05"  # 港股收盘后
    HK_DAYS_OF_WEEK: str = "mon-fri"
    
    # 港股数据模式: "etf" 或 "index"
    HK_DATA_MODE: str = "etf"  # etf模式更稳定
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例 - 延迟加载
settings = None

def get_settings():
    """获取全局配置实例"""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def get_enabled_markets() -> List[str]:
    """获取启用的市场列表"""
    settings = get_settings()
    markets = settings.ENABLED_MARKETS.split(',')
    return [m.strip().lower() for m in markets if m.strip()]


def get_market_config(market: str) -> dict:
    """获取指定市场的配置
    
    Args:
        market: 市场类型 ('a_share', 'us', 'hk')
        
    Returns:
        dict: 市场配置
    """
    settings = get_settings()
    
    configs = {
        'a_share': {
            'enabled': settings.A_SHARE_ENABLED,
            'schedule_time': settings.A_SHARE_SCHEDULE_TIME,
            'days_of_week': settings.A_SHARE_DAYS_OF_WEEK,
        },
        'us': {
            'enabled': settings.US_ENABLED,
            'schedule_time': settings.US_SCHEDULE_TIME,
            'days_of_week': settings.US_DAYS_OF_WEEK,
        },
        'hk': {
            'enabled': settings.HK_ENABLED,
            'schedule_time': settings.HK_SCHEDULE_TIME,
            'days_of_week': settings.HK_DAYS_OF_WEEK,
            'data_mode': settings.HK_DATA_MODE,
        },
    }
    
    return configs.get(market.lower(), {})
