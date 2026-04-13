"""
LLM 服务模块

统一的 LLM 适配器接口，支持多个 Provider。
"""

# 适配器
# 缓存适配器
from backend.services.llm.adapter import (
    CachedAdapter,
    ClaudeAdapter,
    LLMAdapter,
    LocalAdapter,
    OpenAIAdapter,
    OpenAICompatibleAdapter,
    get_llm_adapter,
)

# 预算控制
from backend.services.llm.budget import (
    BudgetLimit,
    BudgetStatus,
    TokenBudget,
    UsageRecord,
    clear_user_budget,
    get_user_budget,
)

# 缓存
from backend.services.llm.cache import (
    CacheEntry,
    LLMCache,
    clear_llm_cache,
    get_llm_cache,
)

# 错误处理
from backend.services.llm.errors import (
    AuthError,
    ContextOverflowError,
    InvalidRequestError,
    LLMError,
    LLMErrorCode,
    ModelNotFoundError,
    NetworkError,
    QuotaError,
    RateLimitError,
    TimeoutError,
    from_http_response,
)

# 管理器
from backend.services.llm.manager import (
    LLMManager,
    ProviderHealth,
    get_llm_manager,
    set_llm_manager,
)

# 模型信息
from backend.services.llm.models import (
    ALL_MODELS,
    CLAUDE_MODELS,
    OLLAMA_MODELS,
    OPENAI_COMPATIBLE_MODELS,
    OPENAI_MODELS,
    ModelInfo,
    get_model_info,
)

# Provider 配置
from backend.services.llm.providers import (
    PROVIDERS,
    PROVIDERS_MAP,
    get_provider_api_format,
    get_provider_endpoint,
    get_provider_info,
    list_provider_values,
    list_providers,
)

# 弹性机制
from backend.services.llm.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    ResilientAdapter,
    with_retry,
)

# SDK 适配器
from backend.services.llm.sdk_adapter import (
    ClaudeSDKAdapter,
    OpenAISDKAdapter,
    SDKAdapter,
    get_sdk_adapter,
)

# 类型定义
from backend.services.llm.types import (
    LLMRequest,
    LLMResponse,
    Message,
    StreamChunk,
    Tool,
    ToolCall,
    ToolResult,
    Usage,
)

__all__ = [
    # 适配器
    "LLMAdapter",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "LocalAdapter",
    "OpenAICompatibleAdapter",
    "CachedAdapter",
    "get_llm_adapter",
    # SDK 适配器
    "SDKAdapter",
    "ClaudeSDKAdapter",
    "OpenAISDKAdapter",
    "get_sdk_adapter",
    # 错误
    "LLMError",
    "LLMErrorCode",
    "RateLimitError",
    "AuthError",
    "QuotaError",
    "InvalidRequestError",
    "ModelNotFoundError",
    "NetworkError",
    "TimeoutError",
    "ContextOverflowError",
    "from_http_response",
    # 模型
    "ModelInfo",
    "get_model_info",
    "ALL_MODELS",
    "CLAUDE_MODELS",
    "OPENAI_MODELS",
    "OPENAI_COMPATIBLE_MODELS",
    "OLLAMA_MODELS",
    # 类型
    "Message",
    "Tool",
    "ToolCall",
    "ToolResult",
    "LLMRequest",
    "LLMResponse",
    "Usage",
    "StreamChunk",
    # Provider
    "PROVIDERS",
    "PROVIDERS_MAP",
    "get_provider_info",
    "get_provider_api_format",
    "list_providers",
    "list_provider_values",
    "get_provider_endpoint",
    # 弹性
    "CircuitBreaker",
    "CircuitOpenError",
    "with_retry",
    "ResilientAdapter",
    # 管理器
    "LLMManager",
    "ProviderHealth",
    "get_llm_manager",
    "set_llm_manager",
    # 预算控制
    "BudgetLimit",
    "BudgetStatus",
    "TokenBudget",
    "UsageRecord",
    "clear_user_budget",
    "get_user_budget",
    # 缓存
    "CacheEntry",
    "LLMCache",
    "clear_llm_cache",
    "get_llm_cache",
]
