"""统一 Rate Limiter 实例

从 main.py 和 auth.py 中提取共享的 Limiter 实例。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# 统一的 Limiter 实例，所有路由共享
limiter = Limiter(key_func=get_remote_address)
