"""
LLM 管理器模块

提供 Provider 健康检查、故障转移、自动降级等功能。
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime

from backend.services.llm.adapter import LLMAdapter, get_llm_adapter
from backend.services.llm.errors import LLMError

logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Provider 健康状态"""
    provider: str
    healthy: bool = False
    latency_ms: float | None = None
    last_check: datetime | None = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class LLMManager:
    """
    LLM 管理器

    负责：
    - 管理多个 Provider 的适配器
    - 健康检查与状态跟踪
    - 自动故障转移
    - Provider 优先级管理
    """

    def __init__(
        self,
        default_provider: str = "claude",
        priority: list[str] | None = None
    ):
        """
        Args:
            default_provider: 默认 Provider
            priority: Provider 优先级列表
        """
        self.default_provider = default_provider
        self.priority = priority or ["claude", "openai", "local"]

        # 适配器缓存
        self._adapters: dict[str, LLMAdapter] = {}

        # 健康状态
        self._health: dict[str, ProviderHealth] = {}
        for provider in self.priority:
            self._health[provider] = ProviderHealth(provider=provider)

        # 健康检查配置
        self.health_check_timeout = 10.0  # 健康检查超时时间
        self.health_check_interval = 60.0  # 健康检查间隔
        self.failure_threshold = 3  # 连续失败阈值
        self.success_threshold = 2  # 连续成功阈值（用于恢复）

        # 锁
        self._lock = asyncio.Lock()

    def get_adapter(self, provider: str) -> LLMAdapter:
        """获取 Provider 的适配器"""
        if provider not in self._adapters:
            self._adapters[provider] = get_llm_adapter(provider)
        return self._adapters[provider]

    async def health_check(self, provider: str) -> ProviderHealth:
        """
        检查 Provider 健康状态

        Args:
            provider: Provider 名称

        Returns:
            ProviderHealth 对象
        """
        health = self._health.get(provider)
        if not health:
            health = ProviderHealth(provider=provider)
            self._health[provider] = health

        start_time = time.time()
        adapter = self.get_adapter(provider)

        try:
            # 使用简单请求进行健康检查
            await asyncio.wait_for(
                adapter.chat(
                    messages=[{"role": "user", "content": "ping"}],
                    system_prompt="You are a helpful assistant.",
                    max_tokens=10
                ),
                timeout=self.health_check_timeout
            )

            # 成功
            health.healthy = True
            health.latency_ms = (time.time() - start_time) * 1000
            health.last_check = datetime.utcnow()
            health.consecutive_failures = 0
            health.consecutive_successes += 1

            logger.debug(
                f"Health check passed for {provider}: "
                f"latency={health.latency_ms:.2f}ms"
            )

        except TimeoutError:
            health.healthy = False
            health.last_check = datetime.utcnow()
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            logger.warning(f"Health check timeout for {provider}")

        except LLMError as e:
            health.healthy = False
            health.last_check = datetime.utcnow()
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            logger.warning(f"Health check failed for {provider}: {e}")

        except Exception as e:
            health.healthy = False
            health.last_check = datetime.utcnow()
            health.consecutive_failures += 1
            health.consecutive_successes = 0
            logger.warning(f"Health check error for {provider}: {e}")

        return health

    async def get_best_provider(self) -> str | None:
        """
        获取最健康的 Provider

        按优先级顺序，返回第一个健康的 Provider。

        Returns:
            Provider 名称，或 None（如果全部不健康）
        """
        for provider in self.priority:
            health = self._health.get(provider)

            # 如果有连续失败，需要达到成功阈值才能恢复
            if (
                health
                and health.consecutive_failures >= self.failure_threshold
                and health.consecutive_successes < self.success_threshold
            ):
                continue

            # 尝试健康检查
            health = await self.health_check(provider)
            if health.healthy:
                return provider

        return None

    async def get_provider_with_fallback(
        self,
        preferred_provider: str | None = None
    ) -> tuple[str, LLMAdapter]:
        """
        获取 Provider，失败时自动降级

        Args:
            preferred_provider: 首选 Provider

        Returns:
            (provider 名称, adapter 实例)

        Raises:
            LLMError: 所有 Provider 都不可用
        """
        providers_to_try = []

        # 如果有首选，优先尝试
        if preferred_provider and preferred_provider in self.priority:
            # 移动到列表开头
            providers_to_try = [preferred_provider] + [
                p for p in self.priority if p != preferred_provider
            ]
        else:
            providers_to_try = list(self.priority)

        last_error = None
        for provider in providers_to_try:
            try:
                adapter = self.get_adapter(provider)

                # 快速健康检查（可选，如果需要更严格可以开启）
                # health = await self.health_check(provider)
                # if not health.healthy:
                #     continue

                return provider, adapter

            except LLMError as e:
                last_error = e
                await self.health_check(provider)  # 更新健康状态
                logger.warning(f"Provider {provider} failed, trying next: {e}")
                continue

        # 所有 Provider 都失败
        if last_error:
            raise last_error
        else:
            raise LLMError(
                code=None,
                message="No available providers",
                provider="unknown"
            )

    async def chat_with_fallback(
        self,
        messages: list[dict],
        system_prompt: str,
        preferred_provider: str | None = None,
        **kwargs
    ) -> tuple[str, str]:
        """
        使用自动降级的 chat 调用

        Args:
            messages: 消息列表
            system_prompt: 系统提示
            preferred_provider: 首选 Provider
            **kwargs: 额外参数

        Returns:
            (响应内容, 实际使用的 provider)
        """
        provider, adapter = await self.get_provider_with_fallback(preferred_provider)

        try:
            response = await adapter.chat(
                messages=messages,
                system_prompt=system_prompt,
                **kwargs
            )
            return response, provider

        except LLMError as e:
            # 更新健康状态
            await self.health_check(provider)

            # 尝试下一个 Provider
            if provider != self.priority[-1]:
                logger.warning(f"Falling back from {provider} due to: {e}")
                return await self.chat_with_fallback(
                    messages, system_prompt,
                    preferred_provider=preferred_provider,
                    **kwargs
                )

            raise e

    def get_health_status(self) -> dict[str, ProviderHealth]:
        """获取所有 Provider 的健康状态"""
        return dict(self._health)

    def get_healthy_providers(self) -> list[str]:
        """获取所有健康的 Provider"""
        return [
            p for p, h in self._health.items()
            if h.healthy and h.consecutive_failures < self.failure_threshold
        ]


# 全局 LLM 管理器实例
_llm_manager: LLMManager | None = None


def get_llm_manager() -> LLMManager:
    """获取全局 LLM 管理器"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager


def set_llm_manager(manager: LLMManager):
    """设置全局 LLM 管理器"""
    global _llm_manager
    _llm_manager = manager
