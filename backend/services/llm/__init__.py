"""
LLM 服务模块

统一的 LLM 适配器接口，支持多个 Provider。
"""

# 适配器
from backend.services.llm.adapter import (
    LLMAdapter,
    ClaudeAdapter,
    OpenAIAdapter,
    LocalAdapter,
    OpenAICompatibleAdapter,
    get_llm_adapter,
)

# 错误处理
from backend.services.llm.errors import (
    LLMError,
    LLMErrorCode,
    RateLimitError,
    AuthError,
    QuotaError,
    InvalidRequestError,
    ModelNotFoundError,
    NetworkError,
    TimeoutError,
    ContextOverflowError,
    from_http_response,
)

# 模型信息
from backend.services.llm.models import (
    ModelInfo,
    get_model_info,
    ALL_MODELS,
    CLAUDE_MODELS,
    OPENAI_MODELS,
    OPENAI_COMPATIBLE_MODELS,
    OLLAMA_MODELS,
)

# 类型定义
from backend.services.llm.types import (
    Message,
    Tool,
    ToolCall,
    ToolResult,
    LLMRequest,
    LLMResponse,
    Usage,
    StreamChunk,
)

# Provider 配置
from backend.services.llm.providers import (
    PROVIDERS,
    PROVIDERS_MAP,
    get_provider_info,
    get_provider_api_format,
    list_providers,
    list_provider_values,
    get_provider_endpoint,
)

# 弹性机制
from backend.services.llm.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    with_retry,
    ResilientAdapter,
)

# 管理器
from backend.services.llm.manager import (
    LLMManager,
    ProviderHealth,
    get_llm_manager,
    set_llm_manager,
)

# 预算控制
from backend.services.llm.budget import (
    TokenBudget,
    BudgetStatus,
    BudgetLimit,
    UsageRecord,
    get_user_budget,
    clear_user_budget,
)

# 缓存
from backend.services.llm.cache import (
    LLMCache,
    CacheEntry,
    get_llm_cache,
    clear_llm_cache,
)

# 缓存适配器
from backend.services.llm.adapter import CachedAdapter

__all__ = [
    # 适配器
    "LLMAdapter",
    "ClaudeAdapter",
    "OpenAIAdapter",
    "LocalAdapter",
    "OpenAICompatibleAdapter",
    "CachedAdapter",
    "get_llm_adapter",
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
]
