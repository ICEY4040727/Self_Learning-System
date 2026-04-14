# 问题 02: `Limiter` 实例在 `main.py` 和 `auth.py` 中重复创建

## 问题类型
重复初始化 / 冗余实例

## 涉及文件
- `backend/main.py` 第 8、14 行
- `backend/api/routes/auth.py` 第 6、16 行

## 重复内容

**`main.py`:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

**`auth.py`:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
```

两个文件各创建了一个 `Limiter` 实例，但 `auth.py` 中的实例仅用于登录接口的 rate limiting（第 93 行 `@_rate_limit`），而 `main.py` 的实例注册到了 `app.state.limiter`（第 38 行）。

## 问题细节

1. **`main.py` 的 limiter**：全局级别，通过 `app.state.limiter` 绑定，注册了异常处理器，但没有直接用在任何路由上
2. **`auth.py` 的 limiter**：局部级别，只用于 `POST /api/auth/login` 的 rate limit（5/分钟），通过 `_rate_limit` 间接引用

两者是独立实例，如果未来 slowapi 的配置（如存储后端、策略）需要调整，必须在两处同步。

## 影响分析

1. **概念混乱**：不清楚哪个 limiter 是"主"实例，新的 rate limit 应该注册到哪个
2. **配置不一致风险**：两个实例可能演化出不同的配置
3. **auth.py 的 limiter 是多余的**：slowapi 的 `@limiter.limit()` 装饰器需要绑定到 `app.state.limiter` 上的同一个实例，auth.py 创建独立实例是错误用法

## 建议修复方向

1. 在 `main.py` 中保留唯一的 limiter 实例
2. 在 `auth.py` 中通过 `from backend.main import limiter` 引用，或提取到独立的 `backend/core/rate_limit.py` 模块
3. 删除 `auth.py` 中的 `Limiter(...)` 实例化