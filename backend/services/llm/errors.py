"""
LLM 错误处理模块

定义结构化错误类型，支持按错误类型进行不同处理。
"""

from enum import Enum
from typing import Optional


class LLMErrorCode(Enum):
    """LLM 错误码枚举"""
    AUTH_FAILED = "auth_failed"           # 401 认证失败
    RATE_LIMITED = "rate_limited"         # 429 限流
    QUOTA_EXCEEDED = "quota_exceeded"     # 配额超限
    INVALID_REQUEST = "invalid_request"   # 400 请求无效
    MODEL_NOT_FOUND = "model_not_found"   # 模型不存在
    NETWORK_ERROR = "network_error"       # 网络错误
    TIMEOUT = "timeout"                  # 超时
    CONTEXT_OVERFLOW = "context_overflow" # 上下文超限
    UNKNOWN = "unknown"                   # 未知错误


class LLMError(Exception):
    """
    LLM 基础错误类
    
    Attributes:
        code: 错误码
        message: 错误消息
        provider: 提供商名称
        status_code: HTTP 状态码
        details: 额外详情
    """
    
    def __init__(
        self,
        code: LLMErrorCode,
        message: str,
        provider: str,
        status_code: Optional[int] = None,
        details: Optional[dict] = None
    ):
        self.code = code
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.details = details or {}
        super().__init__(f"[{provider}] {code.value}: {message}")
    
    def to_dict(self) -> dict:
        """转换为字典，用于 API 响应"""
        return {
            "error_code": self.code.value,
            "message": self.message,
            "provider": self.provider,
            "status_code": self.status_code,
            "details": self.details
        }


class RateLimitError(LLMError):
    """限流错误（429）"""
    
    def __init__(self, provider: str, retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            code=LLMErrorCode.RATE_LIMITED,
            message=f"Rate limited, retry after {retry_after}s" if retry_after else "Rate limited",
            provider=provider,
            status_code=429,
            details=details
        )


class AuthError(LLMError):
    """认证错误（401/403）"""
    
    def __init__(self, provider: str, message: str = "Invalid API key"):
        super().__init__(
            code=LLMErrorCode.AUTH_FAILED,
            message=message,
            provider=provider,
            status_code=401
        )


class QuotaError(LLMError):
    """配额超限错误"""
    
    def __init__(self, provider: str, quota_type: str):
        super().__init__(
            code=LLMErrorCode.QUOTA_EXCEEDED,
            message=f"Quota exceeded for {quota_type}",
            provider=provider,
            details={"quota_type": quota_type}
        )


class InvalidRequestError(LLMError):
    """无效请求错误（400）"""
    
    def __init__(self, provider: str, message: str):
        super().__init__(
            code=LLMErrorCode.INVALID_REQUEST,
            message=message,
            provider=provider,
            status_code=400
        )


class ModelNotFoundError(LLMError):
    """模型不存在错误（404）"""
    
    def __init__(self, provider: str, model: str):
        super().__init__(
            code=LLMErrorCode.MODEL_NOT_FOUND,
            message=f"Model not found: {model}",
            provider=provider,
            status_code=404,
            details={"model": model}
        )


class NetworkError(LLMError):
    """网络错误"""
    
    def __init__(self, provider: str, message: str, details: Optional[dict] = None):
        super().__init__(
            code=LLMErrorCode.NETWORK_ERROR,
            message=message,
            provider=provider,
            details=details
        )


class TimeoutError(LLMError):
    """超时错误"""
    
    def __init__(self, provider: str, timeout: float):
        super().__init__(
            code=LLMErrorCode.TIMEOUT,
            message=f"Request timeout after {timeout}s",
            provider=provider,
            details={"timeout": timeout}
        )


class ContextOverflowError(LLMError):
    """上下文超限错误"""
    
    def __init__(self, provider: str, context_limit: int):
        super().__init__(
            code=LLMErrorCode.CONTEXT_OVERFLOW,
            message=f"Context length exceeds limit of {context_limit} tokens",
            provider=provider,
            status_code=400,
            details={"context_limit": context_limit}
        )


def from_http_response(provider: str, status_code: int, response_body: str) -> LLMError:
    """
    根据 HTTP 响应创建对应的 LLM 错误
    
    Args:
        provider: 提供商名称
        status_code: HTTP 状态码
        response_body: 响应体
    
    Returns:
        对应的 LLM 错误类型
    """
    import json
    
    # 尝试解析错误消息
    message = "Unknown error"
    try:
        data = json.loads(response_body)
        if isinstance(data, dict):
            message = data.get("error", {}).get("message") or data.get("message") or data.get("error", {}).get("type") or response_body
        else:
            message = str(data)
    except (json.JSONDecodeError, TypeError):
        message = response_body[:200] if response_body else "Unknown error"
    
    if status_code == 401 or status_code == 403:
        return AuthError(provider, message)
    elif status_code == 429:
        retry_after = None
        try:
            data = json.loads(response_body)
            retry_after = data.get("retry_after")
        except (json.JSONDecodeError, TypeError):
            pass
        return RateLimitError(provider, retry_after)
    elif status_code == 400:
        if "context" in message.lower() or "length" in message.lower() or "token" in message.lower():
            return ContextOverflowError(provider, 0)
        return InvalidRequestError(provider, message)
    elif status_code == 404:
        return ModelNotFoundError(provider, message)
    else:
        return LLMError(
            code=LLMErrorCode.UNKNOWN,
            message=message,
            provider=provider,
            status_code=status_code
        )
