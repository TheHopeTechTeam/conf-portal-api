"""
Rate limiters dependencies for API endpoints.

限流策略說明：
1. 短期限流（1秒）：防止突發流量，保護系統穩定性
2. 中期限流（30秒）：平滑流量，避免短期內過多請求
3. 長期限流（1小時）：總量控制，防止長期濫用

不同端點類型的限流策略：
- 讀取端點：較寬鬆，因為讀取操作對系統負擔較小
- 寫入端點：較嚴格，因為寫入操作需要更多資源

配置檔案位置：env/rate_limiters.yaml
"""
from fastapi import Depends
from fastapi_limiter.depends import RateLimiter

from portal.config import settings
from portal.schemas.rate_limiter import RateLimiterConfig


def create_rate_limiters(config: RateLimiterConfig) -> list:
    """
    從 RateLimiterConfig Model 建立限流器列表

    :param config: 限流器配置 Model
    :return: 限流器列表
    """
    return [
        Depends(RateLimiter(times=config.short.times, seconds=config.short.seconds)),
        Depends(RateLimiter(times=config.medium.times, seconds=config.medium.seconds)),
        Depends(RateLimiter(times=config.long.times, seconds=config.long.seconds)),
    ]


def get_rate_limiters_config(config_type: str = "default") -> RateLimiterConfig:
    """
    從配置檔案中取得限流器設定

    :param config_type: 配置類型（default, read, write, admin）
    :return:
    """
    if not settings.RATE_LIMITERS_CONFIG:
        # 如果配置未載入，返回預設值
        from portal.schemas.rate_limiter import RateLimitWindow
        return RateLimiterConfig(
            short=RateLimitWindow(times=3, seconds=1),
            medium=RateLimitWindow(times=20, seconds=30),
            long=RateLimitWindow(times=400, seconds=3600),
        )

    # 根據配置類型取得對應的配置
    config_map = {
        "default": settings.RATE_LIMITERS_CONFIG.default,
        "read": settings.RATE_LIMITERS_CONFIG.read,
        "write": settings.RATE_LIMITERS_CONFIG.write,
    }

    return config_map.get(config_type, settings.RATE_LIMITERS_CONFIG.default)


# 預設限流器（用於一般端點）
DEFAULT_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("default"))
# 讀取端點限流器（較寬鬆）
READ_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("read"))
# 寫入端點限流器（較嚴格）
WRITE_RATE_LIMITERS = create_rate_limiters(get_rate_limiters_config("write"))
