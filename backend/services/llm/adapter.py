"""
LLM Adapter 模块

统一的 LLM 适配器接口，支持多个 Provider。
集成错误处理、模型信息、重试机制。
"""

import logging
import time
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Optional, Any

import httpx

from backend.core.config import get_settings
from backend.services.llm.errors import (
    LLMError, RateLimitError, AuthError, InvalidRequestError,
    ModelNotFoundError, NetworkError, from_http_response
)
from backend.services.llm.models import ModelInfo, get_model_info
from backend.services.llm.providers import get_provider_endpoint
from backend.services.llm.types import Tool, ToolCall

logger = logging.getLogger(__name__)


class LLMAdapter(ABC):
    """LLM 适配器基类"""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider 名称"""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """模型名称"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> str:
        """
        发送聊天请求并获取响应

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示
            user_api_key: 用户提供的 API Key（优先级高于配置）
            **kwargs: 额外参数（temperature, max_tokens 等）

        Returns:
            LLM 响应文本

        Raises:
            LLMError: API 调用错误
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式聊天响应

        Args:
            messages: 消息列表
            system_prompt: 系统提示
            user_api_key: 用户提供的 API Key
            **kwargs: 额外参数

        Yields:
            响应文本片段
        """
        pass

    def get_model_info(self) -> ModelInfo:
        """获取模型信息"""
        return get_model_info(self.model)


class ClaudeAdapter(LLMAdapter):
    """Anthropic Claude API 适配器"""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url or "https://api.anthropic.com/v1"
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return "claude"

    @property
    def model(self) -> str:
        return self._model

    def _get_api_key(self, user_api_key: Optional[str] = None) -> str:
        """获取 API Key"""
        if user_api_key:
            return user_api_key
        settings = get_settings()
        return settings.llm_providers.get("claude", {}).get("api_key", "")

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """发送聊天请求到 Claude API"""
        api_key = self._get_api_key(user_api_key)
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 使用模型的 max_tokens 如果未指定
        if max_tokens is None:
            max_tokens = self.get_model_info().max_tokens

        # 转换消息格式
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # 构建请求
        request_data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": claude_messages
        }
        if system_prompt:
            request_data["system"] = system_prompt
        if temperature != 0.7:  # 只有非默认值才传递
            request_data["temperature"] = temperature

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json=request_data,
                    timeout=self._timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                        self.provider, self.model,
                        usage.get("input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                    content = data.get("content", [{}])
                    if content and isinstance(content, list):
                        return content[0].get("text", "")
                    return ""
                else:
                    error = from_http_response(
                        self.provider,
                        response.status_code,
                        response.text
                    )
                    logger.error(f"Claude API error: {error}")
                    raise error

            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Request timeout after {self._timeout}s")
            except httpx.NetworkError as e:
                raise NetworkError(self.provider, f"Network error: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Unexpected error: {str(e)}")

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Claude SSE 流式响应"""
        api_key = self._get_api_key(user_api_key)
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 转换消息格式
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": claude_messages,
            "stream": True
        }
        if system_prompt:
            request_data["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json=request_data,
                    timeout=self._timeout
                ) as response:
                    if response.status_code != 200:
                        error = from_http_response(
                            self.provider,
                            response.status_code,
                            await response.aread()
                        )
                        raise error

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except json.JSONDecodeError:
                                pass
            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Stream timeout after {self._timeout}s")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Stream error: {str(e)}")


class OpenAIAdapter(LLMAdapter):
    """OpenAI API 适配器"""

    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url or "https://api.openai.com/v1"
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    def _get_api_key(self, user_api_key: Optional[str] = None) -> str:
        """获取 API Key"""
        if user_api_key:
            return user_api_key
        settings = get_settings()
        return settings.llm_providers.get("openai", {}).get("api_key", "")

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """发送聊天请求到 OpenAI API"""
        api_key = self._get_api_key(user_api_key)
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 使用模型的 max_tokens 如果未指定
        if max_tokens is None:
            max_tokens = self.get_model_info().max_tokens

        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens
        }
        if temperature != 0.7:
            request_data["temperature"] = temperature

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "content-type": "application/json"
                    },
                    json=request_data,
                    timeout=self._timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                        self.provider, self.model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    )
                    choices = data.get("choices", [{}])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                else:
                    error = from_http_response(
                        self.provider,
                        response.status_code,
                        response.text
                    )
                    logger.error(f"OpenAI API error: {error}")
                    raise error

            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Request timeout after {self._timeout}s")
            except httpx.NetworkError as e:
                raise NetworkError(self.provider, f"Network error: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Unexpected error: {str(e)}")

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """OpenAI SSE 流式响应"""
        api_key = self._get_api_key(user_api_key)
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": openai_messages,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "content-type": "application/json"
                    },
                    json=request_data,
                    timeout=self._timeout
                ) as response:
                    if response.status_code != 200:
                        error = from_http_response(
                            self.provider,
                            response.status_code,
                            await response.aread()
                        )
                        raise error

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass
            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Stream timeout after {self._timeout}s")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Stream error: {str(e)}")


class LocalAdapter(LLMAdapter):
    """本地模型适配器 (Ollama, LM Studio 等)"""

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0
    ):
        self._model = model
        self._base_url = base_url
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return "local"

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """发送聊天请求到本地模型"""
        # 转换消息格式
        local_messages = []
        if system_prompt:
            local_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            local_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": local_messages,
            "stream": False
        }
        if temperature != 0.7:
            request_data["temperature"] = temperature

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=request_data,
                    timeout=self._timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                else:
                    error = from_http_response(
                        self.provider,
                        response.status_code,
                        response.text
                    )
                    logger.error(f"Local model error: {error}")
                    raise error

            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Request timeout after {self._timeout}s")
            except httpx.NetworkError as e:
                raise NetworkError(self.provider, f"Network error: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Unexpected error: {str(e)}")

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """本地模型 SSE 流式响应"""
        # 转换消息格式
        local_messages = []
        if system_prompt:
            local_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            local_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": local_messages,
            "stream": True
        }

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=request_data,
                    timeout=self._timeout
                ) as response:
                    if response.status_code != 200:
                        error = from_http_response(
                            self.provider,
                            response.status_code,
                            await response.aread()
                        )
                        raise error

                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data:
                                    content = data["message"].get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                pass
            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Stream timeout after {self._timeout}s")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Stream error: {str(e)}")


class OpenAICompatibleAdapter(LLMAdapter):
    """OpenAI 兼容 API 适配器 (DeepSeek, Qwen, Groq 等)"""

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    @property
    def provider(self) -> str:
        return "openai-compatible"

    @property
    def model(self) -> str:
        return self._model

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """发送聊天请求到 OpenAI 兼容 API"""
        api_key = user_api_key or self._api_key or ""
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 使用模型的 max_tokens 如果未指定
        if max_tokens is None:
            max_tokens = self.get_model_info().max_tokens

        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens
        }
        if temperature != 0.7:
            request_data["temperature"] = temperature

        headers = {"content-type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=request_data,
                    timeout=self._timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                        self.provider, self.model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    )
                    choices = data.get("choices", [{}])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                    return ""
                else:
                    error = from_http_response(
                        self.provider,
                        response.status_code,
                        response.text
                    )
                    logger.error(f"OpenAI-compatible API error: {error}")
                    raise error

            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Request timeout after {self._timeout}s")
            except httpx.NetworkError as e:
                raise NetworkError(self.provider, f"Network error: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Unexpected error: {str(e)}")

    async def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[Tool],
        system_prompt: str = "",
        user_api_key: str = None,
        temperature: float = 0.7,
        tool_choice: str = "auto",
        **kwargs
    ) -> tuple[str, list[ToolCall]]:
        """
        发送带工具调用的聊天请求
        
        Args:
            messages: 消息列表
            tools: 可用工具列表
            system_prompt: 系统提示
            user_api_key: 用户 API Key
            temperature: 温度参数
            tool_choice: 工具选择策略 ("auto", "any", "none")
        
        Returns:
            (text_response, tool_calls)
        
        Raises:
            LLMError: API 调用错误
        """
        api_key = user_api_key or self._api_key or ""
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # 处理工具消息
            if role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "content": content,
                    "tool_call_id": msg.get("tool_call_id", "")
                })
            else:
                openai_messages.append({
                    "role": role,
                    "content": content
                })

        # 转换工具格式为 OpenAI 格式
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters.model_dump() if hasattr(tool.parameters, 'model_dump') else {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            })

        request_data = {
            "model": self.model,
            "messages": openai_messages,
            "tools": openai_tools,
            "tool_choice": {"type": "function", "function": {"name": tool_choice}} if tool_choice != "auto" else "auto"
        }
        if temperature != 0.7:
            request_data["temperature"] = temperature

        headers = {"content-type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=request_data,
                    timeout=self._timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    logger.info(
                        "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                        self.provider, self.model,
                        usage.get("prompt_tokens", 0),
                        usage.get("completion_tokens", 0),
                    )
                    
                    choices = data.get("choices", [{}])
                    if not choices:
                        return "", []
                    
                    message = choices[0].get("message", {})
                    text_content = message.get("content", "") or ""
                    
                    # 解析工具调用
                    tool_calls = []
                    for tc in message.get("tool_calls", []):
                        func = tc.get("function", {})
                        tool_calls.append(ToolCall(
                            id=tc.get("id", ""),
                            name=func.get("name", ""),
                            arguments=json.loads(func.get("arguments", "{}"))
                        ))
                    
                    return text_content, tool_calls
                else:
                    error = from_http_response(
                        self.provider,
                        response.status_code,
                        response.text
                    )
                    logger.error(f"OpenAI-compatible API error: {error}")
                    raise error

            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Request timeout after {self._timeout}s")
            except httpx.NetworkError as e:
                raise NetworkError(self.provider, f"Network error: {str(e)}")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Unexpected error: {str(e)}")

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """OpenAI 兼容 SSE 流式响应"""
        api_key = user_api_key or self._api_key or ""
        if not api_key:
            raise AuthError(self.provider, "API key not configured")

        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        request_data = {
            "model": self.model,
            "messages": openai_messages,
            "stream": True
        }

        headers = {"content-type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient() as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=request_data,
                    timeout=self._timeout
                ) as response:
                    if response.status_code != 200:
                        error = from_http_response(
                            self.provider,
                            response.status_code,
                            await response.aread()
                        )
                        raise error

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                pass
            except httpx.TimeoutException:
                raise NetworkError(self.provider, f"Stream timeout after {self._timeout}s")
            except LLMError:
                raise
            except Exception as e:
                raise NetworkError(self.provider, f"Stream error: {str(e)}")


def get_llm_adapter(
    provider: str = "claude",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMAdapter:
    """
    工厂函数：获取 LLM 适配器

    Args:
        provider: Provider 名称 (claude, openai, local, deepseek, qwen, etc.)
        model: 模型名称（可选，默认使用配置）
        api_key: API Key（可选）
        base_url: 自定义 Base URL（用于兼容模式）

    Returns:
        LLMAdapter 实例
    """
    from backend.core.config import get_settings
    from backend.services.llm.providers import get_provider_endpoint

    settings = get_settings()

    if provider == "claude":
        model = model or settings.llm_providers.get("claude", {}).get("model", "claude-3-5-sonnet-20241022")
        api_key = api_key or settings.llm_providers.get("claude", {}).get("api_key")
        return ClaudeAdapter(model=model, api_key=api_key)

    elif provider == "openai":
        model = model or settings.llm_providers.get("openai", {}).get("model", "gpt-4")
        api_key = api_key or settings.llm_providers.get("openai", {}).get("api_key")
        return OpenAIAdapter(model=model, api_key=api_key)

    elif provider == "local":
        model = model or "llama3"
        base_url = base_url or settings.llm_providers.get("local", {}).get("base_url", "http://localhost:11434")
        return LocalAdapter(model=model, base_url=base_url)

    else:
        # OpenAI 兼容模式 (deepseek, qwen, groq, etc.)
        model = model or "default"
        base_url = base_url or get_provider_endpoint(provider)
        return OpenAICompatibleAdapter(model=model, api_key=api_key, base_url=base_url)


class CachedAdapter(LLMAdapter):
    """
    带缓存的 LLM 适配器封装
    
    对底层适配器的响应进行缓存，减少重复请求。
    """
    
    def __init__(
        self,
        adapter: LLMAdapter,
        cache: "LLMCache" = None,  # type: ignore
        ttl: float = 3600.0,
        enabled: bool = True
    ):
        """
        初始化缓存适配器
        
        Args:
            adapter: 底层适配器
            cache: 缓存实例，默认使用全局缓存
            ttl: 缓存过期时间（秒）
            enabled: 是否启用缓存
        """
        self._adapter = adapter
        self._cache = cache
        self._ttl = ttl
        self._enabled = enabled
    
    @property
    def provider(self) -> str:
        return self._adapter.provider
    
    @property
    def model(self) -> str:
        return self._adapter.model
    
    def get_cache(self) -> "LLMCache":  # type: ignore
        """获取缓存实例"""
        if self._cache is None:
            from backend.services.llm.cache import get_llm_cache
            self._cache = get_llm_cache()
        return self._cache
    
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> str:
        """带缓存的聊天请求"""
        # 如果缓存被禁用，直接调用底层适配器
        if not self._enabled:
            return await self._adapter.chat(messages, system_prompt, user_api_key, **kwargs)
        
        # 尝试从缓存获取
        cache = self.get_cache()
        cached = cache.get(
            provider=self.provider,
            model=self.model,
            messages=messages,
            system_prompt=system_prompt,
            **kwargs
        )
        
        if cached is not None:
            logger.debug(f"Cache hit for {self.provider}/{self.model}")
            return cached
        
        # 调用底层适配器
        response = await self._adapter.chat(messages, system_prompt, user_api_key, **kwargs)
        
        # 存入缓存
        cache.set(
            provider=self.provider,
            model=self.model,
            messages=messages,
            system_prompt=system_prompt,
            response=response,
            ttl=self._ttl,
            **kwargs
        )
        
        return response
    
    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式响应不支持缓存，直接传递给底层"""
        async for chunk in self._adapter.chat_stream(messages, system_prompt, user_api_key, **kwargs):
            yield chunk
    
    def get_model_info(self) -> ModelInfo:
        """获取模型信息"""
        return self._adapter.get_model_info()
