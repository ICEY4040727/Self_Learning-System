"""
LLM 响应缓存模块

基于请求内容哈希的响应缓存，支持 TTL 过期。
"""

import hashlib
import json
import time
from typing import Optional, Any
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: str
    created_at: float
    ttl: float  # 秒
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl)


class LLMCache:
    """
    LLM 响应缓存
    
    使用 LRU 策略管理缓存，支持 TTL 过期。
    """
    
    def __init__(self, max_size: int = 100, default_ttl: float = 3600.0):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒），默认 1 小时
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def _make_key(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: str,
        **kwargs
    ) -> str:
        """
        生成缓存键
        
        Args:
            provider: Provider 名称
            model: 模型名称
            messages: 消息列表
            system_prompt: 系统提示
            **kwargs: 其他参数
        
        Returns:
            缓存键哈希
        """
        content = json.dumps({
            "provider": provider,
            "model": model,
            "messages": messages,
            "system_prompt": system_prompt,
            # 包含关键参数
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens"),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def get(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: str,
        **kwargs
    ) -> Optional[str]:
        """
        获取缓存的响应
        
        Args:
            provider: Provider 名称
            model: 模型名称
            messages: 消息列表
            system_prompt: 系统提示
            **kwargs: 其他参数
        
        Returns:
            缓存的响应文本，如果未命中或已过期返回 None
        """
        key = self._make_key(provider, model, messages, system_prompt, **kwargs)
        
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # 检查过期
        if entry.is_expired:
            del self._cache[key]
            self._misses += 1
            return None
        
        # 移到末尾（LRU）
        self._cache.move_to_end(key)
        entry.hit_count += 1
        self._hits += 1
        
        return entry.value
    
    def set(
        self,
        provider: str,
        model: str,
        messages: list[dict],
        system_prompt: str,
        response: str,
        ttl: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        设置缓存
        
        Args:
            provider: Provider 名称
            model: 模型名称
            messages: 消息列表
            system_prompt: 系统提示
            response: 响应文本
            ttl: 过期时间（秒），默认使用 default_ttl
            **kwargs: 其他参数
        """
        key = self._make_key(provider, model, messages, system_prompt, **kwargs)
        
        # 如果已满，删除最老的条目
        if len(self._cache) >= self._max_size and key not in self._cache:
            self._cache.popitem(last=False)
        
        self._cache[key] = CacheEntry(
            key=key,
            value=response,
            created_at=time.time(),
            ttl=ttl or self._default_ttl
        )
        self._cache.move_to_end(key)
    
    def invalidate(
        self,
        provider: str = None,
        model: str = None
    ) -> int:
        """
        使缓存失效
        
        Args:
            provider: 可选，按 Provider 过滤
            model: 可选，按模型过滤
        
        Returns:
            删除的条目数
        """
        original_size = len(self._cache)
        
        if provider is None and model is None:
            self._cache.clear()
        else:
            keys_to_delete = []
            for key, entry in self._cache.items():
                # 需要解析 key 获取 provider/model（简化处理，存储时记录）
                # 这里使用另一种方式：记录所有 key 的元信息
                pass  # 简化实现
        
        return original_size - len(self._cache)
    
    def clear(self) -> int:
        """清空所有缓存"""
        size = len(self._cache)
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        return size
    
    def stats(self) -> dict[str, Any]:
        """
        获取缓存统计
        
        Returns:
            {size, max_size, hits, misses, hit_rate}
        """
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate * 100, 2),
        }


# 全局缓存实例
_llm_cache: Optional[LLMCache] = None


def get_llm_cache(
    max_size: int = 100,
    default_ttl: float = 3600.0
) -> LLMCache:
    """
    获取全局 LLM 缓存实例
    
    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间
    
    Returns:
        LLMCache 实例
    """
    global _llm_cache
    if _llm_cache is None:
        _llm_cache = LLMCache(max_size=max_size, default_ttl=default_ttl)
    return _llm_cache


def clear_llm_cache() -> int:
    """清空全局缓存"""
    cache = get_llm_cache()
    return cache.clear()
