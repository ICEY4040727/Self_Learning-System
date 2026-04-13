"""
LLM Provider 配置模块

定义支持的 LLM 提供商列表和配置。
参考 Cline 的 providers.json 设计。

支持的 Provider 列表（参考 Cline 的 42 个 Provider）：
https://github.com/cline/cline/blob/main/src/shared/providers/providers.json
"""

import json
from pathlib import Path
from typing import Literal, TypedDict


class ProviderInfo(TypedDict):
    """Provider 信息"""
    value: str
    label: str
    api_format: Literal["anthropic", "openai", "openai-compatible", "gemini"]


def load_providers() -> list[ProviderInfo]:
    """从 JSON 文件加载 Provider 列表"""
    provider_file = Path(__file__).parent / "providers.json"
    with open(provider_file, encoding="utf-8") as f:
        data = json.load(f)
    return data["list"]


# 加载所有 Provider
PROVIDERS = load_providers()

# Provider 映射，方便快速查找
PROVIDERS_MAP: dict[str, ProviderInfo] = {p["value"]: p for p in PROVIDERS}


def get_provider_info(provider: str) -> ProviderInfo | None:
    """
    获取 Provider 信息

    Args:
        provider: Provider 名称

    Returns:
        ProviderInfo 或 None（如果不存在）
    """
    return PROVIDERS_MAP.get(provider)


def get_provider_api_format(provider: str) -> str:
    """
    获取 Provider 的 API 格式

    Args:
        provider: Provider 名称

    Returns:
        API 格式 ("anthropic" | "openai" | "openai-compatible" | "gemini")
    """
    info = get_provider_info(provider)
    if info:
        return info["api_format"]
    return "openai-compatible"  # 默认


def list_providers() -> list[ProviderInfo]:
    """获取所有 Provider 列表"""
    return PROVIDERS


def list_provider_values() -> list[str]:
    """获取所有 Provider 值列表"""
    return [p["value"] for p in PROVIDERS]


# ============================================================================
# Provider API 端点配置
# ============================================================================

PROVIDER_ENDPOINTS: dict[str, str] = {
    # OpenAI 系列
    "openai": "https://api.openai.com/v1",

    # 中国厂商
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "qwen-code": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "minimax": "https://api.minimax.chat/v1",
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",

    # 海外厂商
    "groq": "https://api.groq.com/openai/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "nebius": "https://api.nebius.ai/v1",
    "xai": "https://api.x.ai/v1",
    "sambanova": "https://api.sambanova.ai/v1",

    # 开源/本地
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
    "huggingface": "https://api-inference.huggingface.co/v1",

    # 聚合服务
    "openrouter": "https://openrouter.ai/api/v1",
    "litellm": "http://localhost:4000/v1",

    # 自定义端点
    "custom": "http://localhost:8000/v1",
}

# Claude (Anthropic) 端点 - 使用不同的 API 格式
ANTHROPIC_ENDPOINT = "https://api.anthropic.com/v1"

# Gemini 端点
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta"


def get_provider_endpoint(provider: str, base_url: str | None = None) -> str:
    """
    获取 Provider 的 API 端点

    Args:
        provider: Provider 名称
        base_url: 自定义 Base URL（用于兼容模式）

    Returns:
        API 端点 URL
    """
    if base_url:
        return base_url.rstrip("/") + "/v1"

    if provider == "claude":
        return ANTHROPIC_ENDPOINT
    elif provider == "gemini":
        return GEMINI_ENDPOINT

    return PROVIDER_ENDPOINTS.get(provider, "http://localhost:11434/v1")


def is_anthropic_provider(provider: str) -> bool:
    """判断是否为 Anthropic 格式的 Provider"""
    return provider == "claude"


def is_openai_provider(provider: str) -> bool:
    """判断是否为 OpenAI 格式的 Provider"""
    return provider == "openai"


def is_openai_compatible_provider(provider: str) -> bool:
    """判断是否为 OpenAI 兼容格式的 Provider"""
    info = get_provider_info(provider)
    if info:
        return info["api_format"] == "openai-compatible"
    # 默认认为未知 Provider 是兼容的
    return True


def is_gemini_provider(provider: str) -> bool:
    """判断是否为 Gemini 格式的 Provider"""
    return provider == "gemini"
