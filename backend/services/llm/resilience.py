from __future__ import annotations

"""
LLM 弹性机制模块

提供重试、熔断器等弹性机制。
"""

import asyncio
import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from backend.services.llm.errors import LLMError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitBreaker:
    """
    熔断器

    当错误率过高时，打开熔断器阻止请求，避免雪崩。

    状态转换:
    - CLOSED: 正常状态，请求通过
    - OPEN: 熔断状态，请求被阻止
    - HALF_OPEN: 半开状态，允许一个测试请求
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        half_open_max_calls: int = 1
    ):
        """
        Args:
            failure_threshold: 打开熔断的连续失败次数
            reset_timeout: 熔断后尝试恢复的时间（秒）
            half_open_max_calls: 半开状态下允许的请求数
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.half_open_max_calls = half_open_max_calls

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = self.STATE_CLOSED
        self.half_open_calls = 0
        self._lock = asyncio.Lock()

    async def is_open(self) -> bool:
        """检查熔断器是否打开"""
        async with self._lock:
            if self.state == self.STATE_OPEN:
                if self.last_failure_time:
                    elapsed = asyncio.get_event_loop().time() - self.last_failure_time
                    if elapsed >= self.reset_timeout:
                        self.state = self.STATE_HALF_OPEN
                        self.half_open_calls = 0
                        logger.info("Circuit breaker entering HALF_OPEN state")
                        return False
                return True
            elif self.state == self.STATE_HALF_OPEN:
                if self.half_open_calls >= self.half_open_max_calls:
                    return True
            return False

    async def record_success(self):
        """记录成功调用"""
        async with self._lock:
            if self.state == self.STATE_HALF_OPEN:
                # 半开状态下的成功调用，关闭熔断器
                self.state = self.STATE_CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED after successful half-open call")
            elif self.state == self.STATE_CLOSED:
                # 正常状态下，重置失败计数
                self.failure_count = 0

    async def record_failure(self):
        """记录失败调用"""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = asyncio.get_event_loop().time()

            if self.state == self.STATE_HALF_OPEN:
                # 半开状态下失败，重新打开熔断器
                self.state = self.STATE_OPEN
                logger.warning("Circuit breaker re-OPENED after half-open failure")
            elif self.state == self.STATE_CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = self.STATE_OPEN
                    logger.warning(f"Circuit breaker OPENED after {self.failure_count} consecutive failures")

    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        通过熔断器执行函数

        Args:
            func: 要执行的异步函数
            *args, **kwargs: 函数参数

        Returns:
            函数返回值

        Raises:
            CircuitOpenError: 熔断器打开时抛出
        """
        if await self.is_open():
            raise CircuitOpenError(f"Circuit breaker is {self.state}")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception:
            await self.record_failure()
            raise


class CircuitOpenError(Exception):
    """熔断器打开错误"""
    pass


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retry_on_rate_limit: bool = True,
    retry_on_timeout: bool = True,
    retry_on_server_error: bool = True
):
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        retry_on_rate_limit: 是否重试限流错误
        retry_on_timeout: 是否重试超时错误
        retry_on_server_error: 是否重试服务器错误（5xx）

    Example:
        @with_retry(max_retries=3, base_delay=1.0)
        async def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if not retry_on_rate_limit or attempt >= max_retries:
                        raise

                    retry_after = e.details.get("retry_after")
                    delay = _calculate_delay(
                        attempt, base_delay, max_delay, exponential_base,
                        custom_delay=retry_after
                    )
                    logger.warning(
                        f"Rate limited, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                except TimeoutError as e:
                    last_exception = e
                    if not retry_on_timeout or attempt >= max_retries:
                        raise

                    delay = _calculate_delay(attempt, base_delay, max_delay, exponential_base)
                    logger.warning(
                        f"Timeout, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                except LLMError as e:
                    last_exception = e
                    # 检查是否是服务器错误
                    is_server_error = (
                        retry_on_server_error and
                        e.status_code is not None and
                        500 <= e.status_code < 600
                    )

                    if not is_server_error or attempt >= max_retries:
                        raise

                    delay = _calculate_delay(attempt, base_delay, max_delay, exponential_base)
                    logger.warning(
                        f"Server error {e.status_code}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

                except Exception as e:
                    last_exception = e
                    if attempt >= max_retries:
                        raise

                    delay = _calculate_delay(attempt, base_delay, max_delay, exponential_base)
                    logger.warning(
                        f"Error: {type(e).__name__}: {e}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def _calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    custom_delay: float | None = None
) -> float:
    """
    计算重试延迟

    Args:
        attempt: 当前尝试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        exponential_base: 指数基数
        custom_delay: 自定义延迟（用于 rate limit 的 retry_after）

    Returns:
        延迟时间（秒）
    """
    if custom_delay is not None:
        return min(custom_delay, max_delay)

    delay = base_delay * (exponential_base ** attempt)
    return min(delay, max_delay)


class ResilientAdapter:
    """
    弹性适配器包装器

    为 LLM Adapter 添加重试和熔断功能。
    """

    def __init__(
        self,
        adapter: LLMAdapter,
        max_retries: int = 3,
        circuit_breaker: CircuitBreaker | None = None
    ):
        """
        Args:
            adapter: 底层 LLM Adapter
            max_retries: 最大重试次数
            circuit_breaker: 熔断器实例
        """
        self.adapter = adapter
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def chat(self, *args, **kwargs) -> str:
        """带弹性的 chat 调用"""
        return await self.circuit_breaker.call(
            with_retry(max_retries=self.max_retries)(self.adapter.chat),
            *args, **kwargs
        )

    async def chat_stream(self, *args, **kwargs):
        """带弹性的 chat_stream 调用"""
        # 流式调用不支持熔断器（因为已经开始流式传输）
        retry_func = with_retry(max_retries=self.max_retries)(self.adapter.chat_stream)
        return await retry_func(*args, **kwargs)

    @property
    def provider(self) -> str:
        """获取底层 Adapter 的 provider"""
        return self.adapter.provider

    @property
    def model(self) -> str:
        """获取底层 Adapter 的 model"""
        return self.adapter.model
