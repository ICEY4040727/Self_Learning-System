"""
官方 SDK 适配器模块

使用官方 SDK（anthropic, openai）实现的适配器。
提供更稳定、更多特性的 LLM 调用。
"""

import logging
from abc import abstractmethod
from collections.abc import AsyncGenerator
from typing import Optional

import httpx

from backend.core.config import get_settings
from backend.services.llm.errors import (
    LLMError, RateLimitError, AuthError, InvalidRequestError,
    NetworkError, TimeoutError, from_http_response
)
from backend.services.llm.models import ModelInfo, get_model_info
from backend.services.llm.types import Tool, ToolCall

logger = logging.getLogger(__name__)


class SDKAdapter:
    """SDK 适配器基类（保持与原有接口兼容）"""
    
    @property
    @abstractmethod
    def provider(self) -> str:
        pass
    
    @property
    @abstractmethod
    def model(self) -> str:
        pass
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> str:
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        pass
    
    def get_model_info(self) -> ModelInfo:
        return get_model_info(self.model)


class ClaudeSDKAdapter(SDKAdapter):
    """
    Anthropic Claude SDK 适配器
    
    使用官方 anthropic SDK，支持：
    - 自动重试
    - Model Caching
    - 官方 Tool Use
    - SSE 流式
    """
    
    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        timeout: float = 60.0
    ):
        try:
            from anthropic import AsyncAnthropic
        except ImportError:
            raise ImportError(
                "anthropic SDK 未安装。请运行: pip install anthropic>=0.25.0"
            )
        
        self._model = model
        self._api_key = api_key
        self._timeout = timeout
        self._client: Optional["AsyncAnthropic"] = None
    
    @property
    def provider(self) -> str:
        return "claude-sdk"
    
    @property
    def model(self) -> str:
        return self._model
    
    def _get_client(self, user_api_key: Optional[str] = None) -> "AsyncAnthropic":
        """获取或创建客户端"""
        from anthropic import AsyncAnthropic
        
        api_key = user_api_key or self._api_key
        if not api_key:
            settings = get_settings()
            api_key = settings.llm_providers.get("claude", {}).get("api_key", "")
        
        if not api_key:
            raise AuthError(self.provider, "API key not configured")
        
        return AsyncAnthropic(api_key=api_key)
    
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: list[Tool] = None,
        **kwargs
    ) -> str:
        """发送聊天请求到 Claude API"""
        client = self._get_client(user_api_key)
        
        if max_tokens is None:
            max_tokens = self.get_model_info().max_tokens
        
        # 转换消息格式
        claude_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # 处理工具结果消息
            if role == "tool":
                claude_messages.append({
                    "role": "user",  # Claude 需要工具结果作为 user 消息
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id", ""),
                        "content": content
                    }]
                })
            else:
                claude_messages.append({
                    "role": role,
                    "content": content
                })
        
        # 转换工具格式
        claude_tools = None
        if tools:
            claude_tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters.model_dump() if hasattr(tool.parameters, 'model_dump') else {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
                for tool in tools
            ]
        
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None,
                messages=claude_messages,
                temperature=temperature if temperature != 0.7 else None,
                tools=claude_tools,
            )
            
            # 记录使用量
            logger.info(
                "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                self.provider, self.model,
                response.usage.input_tokens,
                response.usage.output_tokens,
            )
            
            # 处理响应内容
            if response.content:
                for block in response.content:
                    if block.type == "text":
                        return block.text
            
            return ""
            
        except Exception as e:
            logger.error(f"Claude SDK error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Claude SSE 流式响应"""
        client = self._get_client(user_api_key)
        
        # 转换消息格式
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        try:
            async with client.messages.stream(
                model=self.model,
                max_tokens=1024,
                system=system_prompt if system_prompt else None,
                messages=claude_messages,
                temperature=temperature if temperature != 0.7 else None,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Claude SDK stream error: {e}")
            raise


class OpenAISDKAdapter(SDKAdapter):
    """
    OpenAI SDK 适配器
    
    使用官方 openai SDK，支持：
    - 自动重试
    - Function Calling
    - SSE 流式
    """
    
    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0
    ):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError(
                "openai SDK 未安装。请运行: pip install openai>=1.30.0"
            )
        
        self._model = model
        self._api_key = api_key
        self._base_url = base_url or "https://api.openai.com/v1"
        self._timeout = timeout
        self._client: Optional["AsyncOpenAI"] = None
    
    @property
    def provider(self) -> str:
        return "openai-sdk"
    
    @property
    def model(self) -> str:
        return self._model
    
    def _get_client(self, user_api_key: Optional[str] = None) -> "AsyncOpenAI":
        """获取或创建客户端"""
        from openai import AsyncOpenAI
        
        api_key = user_api_key or self._api_key
        if not api_key:
            settings = get_settings()
            api_key = settings.llm_providers.get("openai", {}).get("api_key", "")
        
        if not api_key:
            raise AuthError(self.provider, "API key not configured")
        
        return AsyncOpenAI(api_key=api_key, base_url=self._base_url)
    
    async def chat(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: list[Tool] = None,
        **kwargs
    ) -> str:
        """发送聊天请求到 OpenAI API"""
        client = self._get_client(user_api_key)
        
        if max_tokens is None:
            max_tokens = self.get_model_info().max_tokens
        
        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # 处理工具结果消息
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
        
        # 转换工具格式
        openai_tools = None
        if tools:
            openai_tools = [
                {
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
                }
                for tool in tools
            ]
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature if temperature != 0.7 else None,
                tools=openai_tools,
            )
            
            # 记录使用量
            usage = response.usage
            logger.info(
                "LLM usage: provider=%s model=%s in_tokens=%d out_tokens=%d",
                self.provider, self.model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )
            
            # 处理响应
            message = response.choices[0].message
            if message.content:
                return message.content
            
            # 处理工具调用
            if message.tool_calls:
                # 返回空字符串，让调用方处理工具调用
                return ""
            
            return ""
            
        except Exception as e:
            logger.error(f"OpenAI SDK error: {e}")
            raise
    
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
        """发送带工具调用的聊天请求"""
        client = self._get_client(user_api_key)
        
        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
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
        
        # 转换工具格式
        openai_tools = [
            {
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
            }
            for tool in tools
        ]
        
        # 工具选择
        if tool_choice == "none":
            tool_choice_arg = None
        elif tool_choice == "any":
            tool_choice_arg = {"type": "function", "function": {"name": ""}}
        else:  # auto
            tool_choice_arg = "auto"
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=openai_tools,
                tool_choice=tool_choice_arg,
                temperature=temperature if temperature != 0.7 else None,
            )
            
            message = response.choices[0].message
            text_content = message.content or ""
            
            # 解析工具调用
            tool_calls = []
            if message.tool_calls:
                import json
                for tc in message.tool_calls:
                    func = tc.function
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=func.name,
                        arguments=json.loads(func.arguments)
                    ))
            
            return text_content, tool_calls
            
        except Exception as e:
            logger.error(f"OpenAI SDK tool calling error: {e}")
            raise
    
    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str,
        user_api_key: str = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """OpenAI SSE 流式响应"""
        client = self._get_client(user_api_key)
        
        # 转换消息格式
        openai_messages = []
        if system_prompt:
            openai_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            openai_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        try:
            stream = await client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                stream=True,
                temperature=temperature if temperature != 0.7 else None,
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI SDK stream error: {e}")
            raise


def get_sdk_adapter(
    provider: str = "claude",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> SDKAdapter:
    """
    工厂函数：获取 SDK 适配器
    
    Args:
        provider: Provider 名称 (claude-sdk, openai-sdk)
        model: 模型名称
        api_key: API Key
        base_url: Base URL (OpenAI 兼容)
    
    Returns:
        SDKAdapter 实例
    """
    settings = get_settings()
    
    if provider in ("claude", "claude-sdk"):
        model = model or settings.llm_providers.get("claude", {}).get("model", "claude-3-5-sonnet-20241022")
        api_key = api_key or settings.llm_providers.get("claude", {}).get("api_key")
        return ClaudeSDKAdapter(model=model, api_key=api_key)
    
    elif provider in ("openai", "openai-sdk"):
        model = model or settings.llm_providers.get("openai", {}).get("model", "gpt-4")
        api_key = api_key or settings.llm_providers.get("openai", {}).get("api_key")
        base_url = base_url or settings.llm_providers.get("openai", {}).get("base_url")
        return OpenAISDKAdapter(model=model, api_key=api_key, base_url=base_url)
    
    else:
        raise ValueError(f"不支持的 SDK Provider: {provider}")
